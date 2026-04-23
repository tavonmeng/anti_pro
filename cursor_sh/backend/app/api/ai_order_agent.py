"""
订单查询 Agent — 独立模块
负责订单的智能查询、筛选、详情展示、状态概览等全部能力。
"""

import re
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.config import settings
from app.utils.security import decode_access_token

order_router = APIRouter()


# ───────────────────────────────────────────────────────
# 数据模型
# ───────────────────────────────────────────────────────

class QueryOrdersRequest(BaseModel):
    message: str
    history: list = []


# ───────────────────────────────────────────────────────
# 常量 & 映射
# ───────────────────────────────────────────────────────

_STATUS_MAP = {
    "draft": "草稿", "pending_assign": "待分配", "in_production": "制作中",
    "pending_review": "待审核", "review_rejected": "审核驳回",
    "preview_ready": "初稿就绪", "final_preview": "终稿就绪",
    "revision_needed": "需修改", "completed": "已完成", "cancelled": "已取消"
}

_TYPE_MAP = {
    "video_purchase": "裸眼3D成片购买适配",
    "ai_3d_custom": "AI裸眼3D内容定制",
    "digital_art": "数字艺术内容定制"
}

# 状态关键词 → 状态值的双向映射
_STATUS_KW_MAP = {
    "待分配": "pending_assign", "制作中": "in_production",
    "待审核": "pending_review", "审核驳回": "review_rejected",
    "初稿": "preview_ready", "终稿": "final_preview",
    "需修改": "revision_needed", "已完成": "completed",
    "草稿": "draft",
}

# 搜索时需要扫描的业务字段
_SEARCH_FIELDS = [
    "brand", "content", "description", "city", "style",
    "target_group", "brand_tone", "background",
    "prohibited_content", "technology", "media_size",
    "sales_contact", "artDirection", "customDirection",
]

# 提取搜索关键词时需要过滤掉的噪音词
_NOISE_WORDS = [
    "看一下", "看下", "列出", "展示", "显示", "查看", "搜索", "查询", "获取", "告诉我", "给我", "帮我",
    "订单", "单子", "单", "的那个", "那个", "这个", "帮我看", "帮我查",
    "看看", "查查", "查一下", "找一下", "找找", "关于", "有关",
    "请", "想看", "想查", "具体", "详情", "详细",
    "有几个", "有多少", "有哪些", "都有哪些", "都有什么",
    "是不是", "有好几个", "有没有", "是否",
    "所有", "全部", "都", "一共", "多少",
    "我的", "我",
    "怎么样了", "怎么样", "什么情况", "进展如何", "进展怎样",
    "进展", "进度", "到哪一步了", "到哪一步", "到什么阶段",
    "什么状态", "还好吗", "顺利吗", "了",
    "还有", "哪些", "没有", "没",
    "还在", "正在", "目前", "现在",
    "上个月", "这个月", "最近", "本周", "上周",
    "的",
]


# ───────────────────────────────────────────────────────
# 工具函数
# ───────────────────────────────────────────────────────

def _get_status_val(o: dict) -> str:
    val = o.get("status", "")
    return val.value if hasattr(val, 'value') else val


def _get_status_text(o: dict) -> str:
    return _STATUS_MAP.get(_get_status_val(o), _get_status_val(o))


def _get_type_text(o: dict) -> str:
    val = o.get("orderType") or o.get("order_type", "")
    if hasattr(val, 'value'):
        val = val.value
    return _TYPE_MAP.get(val, val)


def _get_order_num(o: dict) -> str:
    return o.get("orderNumber") or o.get("order_number", "N/A")


def _extract_search_keyword(user_msg: str) -> str:
    """从用户消息中提取业务搜索关键词"""
    clean_msg = user_msg
    for w in _NOISE_WORDS:
        clean_msg = clean_msg.replace(w, "")
    return clean_msg.strip()


# ───────────────────────────────────────────────────────
# 匹配策略
# ───────────────────────────────────────────────────────

def _try_match_order_by_index(user_msg: str, orders: list) -> dict | None:
    """通过序号匹配，如 '第3个'、'第三个'、'3号'"""
    cn_num_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                  "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

    m = re.search(r'第([一二三四五六七八九十\d]+)[个条项号]', user_msg)
    if not m:
        m = re.search(r'(\d+)[号]', user_msg)
    if not m:
        stripped = user_msg.strip()
        if stripped.isdigit() and 1 <= int(stripped) <= len(orders):
            return orders[int(stripped) - 1]
        return None

    num_str = m.group(1)
    idx = int(num_str) if num_str.isdigit() else cn_num_map.get(num_str, 0)
    if 1 <= idx <= len(orders):
        return orders[idx - 1]
    return None


def _try_match_order_by_order_number(user_msg: str, orders: list) -> dict | None:
    """通过订单号精确匹配，如 'ORD-20260418-TZ3K'"""
    m = re.search(r'(ORD-\d{8}-[A-Z0-9]{4})', user_msg, re.IGNORECASE)
    if m:
        target = m.group(1).upper()
        for o in orders:
            if _get_order_num(o).upper() == target:
                return o
    return None


def _try_match_order_by_keyword(user_msg: str, orders: list) -> dict | None:
    """通过状态关键词匹配，如 '制作中的'、'最新的那个'"""
    if any(kw in user_msg for kw in ["最新", "最近", "最后一个", "第一个"]):
        return orders[0] if orders else None

    for kw, status_val in _STATUS_KW_MAP.items():
        if kw in user_msg:
            for o in orders:
                if _get_status_val(o) == status_val:
                    return o
    return None


def _score_order_match(keyword: str, o: dict) -> int:
    """对单个订单计算与关键词的匹配得分"""
    score = 0
    for field in _SEARCH_FIELDS:
        field_val = o.get(field, "")
        if not field_val or not isinstance(field_val, str):
            continue
        if keyword in field_val or field_val in keyword:
            score += 10 if field in ["brand", "city"] else 5
        else:
            for char in keyword:
                if char in field_val and len(char.strip()) > 0:
                    score += 1
    return score


def _try_search_order_by_content(user_msg: str, orders: list) -> dict | None:
    """业务字段搜索，返回单个最佳匹配"""
    keyword = _extract_search_keyword(user_msg)
    if not keyword:
        return None
    best_match, best_score = None, 0
    for o in orders:
        score = _score_order_match(keyword, o)
        if score > best_score and score >= 3:
            best_score = score
            best_match = o
    return best_match


def _search_all_matching_orders(user_msg: str, orders: list) -> list:
    """业务字段搜索，返回所有匹配的订单"""
    keyword = _extract_search_keyword(user_msg)
    if not keyword:
        return []
    return [o for o in orders if _score_order_match(keyword, o) >= 3]


def _filter_orders_by_status(user_msg: str, orders: list) -> list:
    """按状态关键词筛选，返回所有匹配的订单列表
    
    示例：'哪些订单还在制作中' → 返回所有 in_production 的订单
    """
    matched = []
    for kw, status_val in _STATUS_KW_MAP.items():
        if kw in user_msg:
            for o in orders:
                if _get_status_val(o) == status_val and o not in matched:
                    matched.append(o)
    return matched


def _filter_orders_by_time(user_msg: str, orders: list) -> list:
    """按时间范围筛选订单
    
    示例：'上个月的订单'、'最近一周下的单'、'这个月的'
    """
    now = datetime.now()
    start_date = None

    if "上个月" in user_msg:
        first_of_this_month = now.replace(day=1)
        last_month_end = first_of_this_month - timedelta(days=1)
        start_date = last_month_end.replace(day=1)
        end_date = first_of_this_month
    elif "这个月" in user_msg or "本月" in user_msg:
        start_date = now.replace(day=1)
        end_date = now + timedelta(days=1)
    elif "上周" in user_msg:
        days_since_monday = now.weekday()
        this_monday = now - timedelta(days=days_since_monday)
        start_date = this_monday - timedelta(days=7)
        end_date = this_monday
    elif "本周" in user_msg or "这周" in user_msg:
        days_since_monday = now.weekday()
        start_date = now - timedelta(days=days_since_monday)
        end_date = now + timedelta(days=1)
    elif re.search(r'最近.{0,2}周', user_msg):
        start_date = now - timedelta(days=7)
        end_date = now + timedelta(days=1)
    elif re.search(r'最近.{0,2}(天|日)', user_msg):
        m = re.search(r'最近(\d+)', user_msg)
        days = int(m.group(1)) if m else 7
        start_date = now - timedelta(days=days)
        end_date = now + timedelta(days=1)

    if not start_date:
        return []

    matched = []
    for o in orders:
        created = o.get("createdAt") or o.get("created_at", "")
        if not created:
            continue
        try:
            order_date = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=None)
            if start_date <= order_date < end_date:
                matched.append(o)
        except (ValueError, TypeError):
            continue
    return matched


# ───────────────────────────────────────────────────────
# 响应构建
# ───────────────────────────────────────────────────────

def _build_status_narrative(o: dict) -> str:
    """根据订单状态生成专业的顾问式叙述"""
    status_val = _get_status_val(o)
    brand = o.get("brand", "")
    type_text = _get_type_text(o)
    ref = f"「{brand}」" if brand else f"「{type_text}」"

    narratives = {
        "pending_assign": f"{ref}项目已确认立项，目前处于前期资源统筹阶段，即将介入核心制作流程。",
        "in_production": f"{ref}项目已顺畅进入制作周期。我们将严格把控质量节点，并在合适阶段输出相关进展。",
        "pending_review": f"{ref}项目已产出阶段性交付物，当前正进行内部品控审核，确认达标后将向您开放预览。",
        "review_rejected": f"{ref}项目的近期产出反馈触发了内部品控标准拦截，技术组正针对偏差项进行迭代校准。",
        "preview_ready": f"{ref}项目的初版预览已封装出档，请评估审阅并同步指导意见。",
        "final_preview": f"{ref}项目的终检版本已生成，提请您做最终阶段验收。确认无误后将流转至正式交付步骤。",
        "revision_needed": f"{ref}项目正根据反馈意见进行针对性调整，完成后将重新提交预览供您确认。",
        "completed": f"{ref}项目已通过验收并正式交付归档。各项资产数据已锁定，若有衍生技术需求可随时沟通。",
        "draft": f"{ref}项目当前仍滞留于需求评估与草拟表单阶段。您可以进一步丰富业务细节或直接启动激活序列。",
    }
    return narratives.get(status_val, f"以下是 {ref} 项目（{_get_status_text(o)}）的具体指标与流转动态。")


def _build_order_detail_message(o: dict) -> str:
    """构建订单详情的自然语言描述"""
    narrative = _build_status_narrative(o)
    return f"{narrative}\n\n点击下方卡片可查看完整订单详情，如需了解其他订单或有新需求，随时告知。"


def _build_rich_order_summary(orders: list) -> str:
    """构建包含业务字段的富摘要，供 LLM 匹配使用"""
    lines = []
    for i, o in enumerate(orders, 1):
        parts = [f"{i}. 订单号 {_get_order_num(o)} | {_get_type_text(o)} | 状态：{_get_status_text(o)}"]
        for field, label in [("brand", "品牌"), ("city", "城市"), ("style", "风格")]:
            val = o.get(field, "")
            if val:
                parts.append(f"{label}:{val}")
        content = o.get("content", "") or o.get("description", "")
        if content:
            parts.append(f"内容:{content[:50]}")
        bg = o.get("background", "")
        if bg:
            parts.append(f"背景:{bg[:30]}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _build_order_list_summary(orders: list) -> str:
    """构建订单列表的文字摘要"""
    summary_lines = []
    for i, o in enumerate(orders, 1):
        summary_lines.append(
            f"{i}. 订单号 {_get_order_num(o)} | {_get_type_text(o)} | 状态：{_get_status_text(o)}"
        )
    return "\n".join(summary_lines)


def _build_status_overview(orders: list) -> str:
    """生成自然语言的状态概览"""
    counts: dict[str, int] = {}
    for o in orders:
        st = _get_status_text(o)
        counts[st] = counts.get(st, 0) + 1

    priority = ["制作中", "待审核", "需修改", "待分配", "初稿就绪", "终稿就绪", "审核驳回", "已完成", "草稿"]
    parts = [f"{counts[s]}个{s}" for s in priority if counts.get(s, 0) > 0]
    for s, c in counts.items():
        if s not in priority and c > 0:
            parts.append(f"{c}个{s}")
    return "、".join(parts)


# ───────────────────────────────────────────────────────
# LLM 集成
# ───────────────────────────────────────────────────────

async def _llm_match_order(user_msg: str, history: list, orders_summary: str) -> int | None:
    """使用 LLM 理解用户自然语言，返回匹配的订单序号"""
    if not settings.AI_API_KEY:
        return None

    try:
        prompt = (
            "你是一个订单匹配助手。根据用户的消息和对话历史，判断用户想查看哪个订单的详情。\n\n"
            f"当前订单列表（含业务信息）：\n{orders_summary}\n\n"
            "规则：\n"
            "- 如果用户通过序号、订单号、品牌名、城市、内容描述等任何方式指定了某个订单，返回该订单的序号数字\n"
            "- 如果用户提到的关键词能唯一匹配到某个订单，返回该订单序号\n"
            "- 如果有多个匹配或无法判断，返回 0\n"
            "- 只返回一个数字，不要返回任何其他内容"
        )

        llm_messages = [{"role": "system", "content": prompt}]
        recent = [h for h in history if h.get("role") in ["user", "assistant"] and h.get("content")][-6:]
        for h in recent:
            llm_messages.append({"role": h["role"], "content": h["content"]})
        llm_messages.append({"role": "user", "content": user_msg})

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.AI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.AI_MODEL_NAME,
                    "messages": llm_messages,
                    "max_tokens": 10,
                    "temperature": 0
                },
                timeout=10.0
            )
            resp.raise_for_status()
            result = resp.json()["choices"][0]["message"]["content"].strip()
            if result.isdigit():
                idx = int(result)
                return idx if idx > 0 else None
    except Exception as e:
        print(f"LLM 订单匹配失败: {e}")
    return None


# ───────────────────────────────────────────────────────
# 意图检测
# ───────────────────────────────────────────────────────

def _is_filter_query(user_msg: str) -> bool:
    """判断是否为筛选查询（想看多个匹配结果）
    
    覆盖场景：
    - 量词类：'成都有几个订单'
    - 枚举类：'耐克的订单有哪些'
    - 状态概览类：'成都的订单怎么样了'
    - 状态筛选类：'哪些订单还在制作中'
    - 否定筛选类：'还有哪些没完成的'
    - 时间筛选类：'上个月的订单'
    """
    # ── 量词/枚举信号 ──
    filter_patterns = [
        r'有几个', r'有多少', r'有哪些', r'都有哪些', r'都有什么',
        r'有好几个', r'是不是有', r'有没有', r'是否有',
        r'一共有', r'总共有', r'多少个',
        r'全部.*订单', r'所有.*订单',
        r'订单都', r'单子都',
        r'哪些订单', r'哪些单',
        r'列一下', r'统计', r'汇总',
    ]
    for p in filter_patterns:
        if re.search(p, user_msg):
            return True

    # ── 状态概览式：「X的订单 + 怎么样/进展」 ──
    if re.search(r'[\u4e00-\u9fa5a-zA-Z]+的?(订单|单子|单)', user_msg):
        status_suffixes = [
            r'怎么样', r'什么情况', r'进展', r'进度',
            r'到哪一步', r'到什么阶段', r'什么状态',
            r'还好吗', r'顺利吗',
        ]
        for s in status_suffixes:
            if re.search(s, user_msg):
                return True

    # ── 检索概览式：「看下成都的单子」 ──
    if re.search(r'(看下|看一下|查看|看看|查询|搜索|搜一下|列出|帮我找|找找).*的?(订单|单子|单|项目)', user_msg):
        return True

    # ── 状态筛选：'哪些还在制作中'、'制作中的订单有哪些' ──
    for kw in _STATUS_KW_MAP:
        if kw in user_msg:
            if re.search(r'(哪些|有几|有多少|还有|都|还在)', user_msg):
                return True

    # ── 否定筛选：'还有哪些没完成的'、'没完成的订单' ──
    if re.search(r'(没|未|不是).{0,4}(完成|交付|结束)', user_msg):
        return True

    # ── 时间筛选：'上个月的订单'、'最近一周的单' ──
    if re.search(r'(上个月|这个月|本月|上周|本周|这周|最近.{0,3}(周|天|日|月))', user_msg):
        return True

    return False


def _is_detail_query(user_msg: str, history: list) -> bool:
    """判断是否为单个订单详情查询"""
    if _is_filter_query(user_msg):
        return False

    # 强信号
    strong_patterns = [
        r'第[一二三四五六七八九十\d]+[个条项号]',
        r'^\d{1,2}$',
        r'ORD-\d{8}-',
    ]
    for p in strong_patterns:
        if re.search(p, user_msg):
            return True

    # 弱信号（需列表上下文）
    has_list = any(
        "订单号" in h.get("content", "") and "状态" in h.get("content", "")
        for h in history if h.get("role") == "assistant"
    )
    if has_list:
        weak_patterns = [
            r'看看|详情|详细|具体',
            r'最新|最近|最后|第一',
            r'那个|这个|哪个',
            r'待分配|制作中|待审核|需修改|已完成|初稿|终稿',
        ]
        for p in weak_patterns:
            if re.search(p, user_msg):
                return True
        if len(user_msg.strip()) < 15:
            return True

    # 业务关键词信号
    pure_list = ["查看我的订单", "查看订单", "我的订单", "所有订单", "全部订单"]
    if user_msg.strip() in pure_list:
        return False

    m = re.search(r'[\u4e00-\u9fa5a-zA-Z]{1,10}(的|那个)(订单|单子|单)', user_msg)
    if m:
        generic = ["我的订单", "我的单", "全部的订单", "所有的订单"]
        if m.group(0) not in generic:
            return True

    return False


# ───────────────────────────────────────────────────────
# 主路由
# ───────────────────────────────────────────────────────

@order_router.post("/query-orders")
async def ai_query_orders(request: QueryOrdersRequest, raw_request: Request):
    """订单查询 Agent 主入口 — 支持列表、筛选、详情、时间范围等查询"""
    from app.database import async_session_maker
    from app.services.order_service import OrderService
    from app.models.user import User
    from sqlalchemy import select

    # ── 鉴权 ──
    user_id = "anonymous"
    auth_header = raw_request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        payload = decode_access_token(auth_header[7:])
        if payload:
            user_id = payload.get("user_id", "anonymous")

    if user_id == "anonymous":
        return {
            "message": "抱歉，我需要先确认您的身份才能查询订单。请确保您已登录。",
            "orders": []
        }

    # ── 获取订单数据 ──
    orders_data = []
    try:
        async with async_session_maker() as db:
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if user:
                orders = await OrderService.get_orders(db, user)
                user_msg = request.message
                active, drafts = [], []

                for o in orders:
                    sv = _get_status_val(o)
                    if sv == "cancelled":
                        continue
                    if sv == "completed":
                        if "已完成" in user_msg or "完成" in user_msg:
                            active.append(o)
                        continue
                    if sv == "draft":
                        if "草稿" in user_msg:
                            drafts.append(o)
                    else:
                        active.append(o)

                orders_data = (active + drafts)[:10]
    except Exception as e:
        print(f"查询订单失败: {e}")
        return {"message": "非常抱歉，查询订单时遇到了问题，请稍后再试。", "orders": []}

    if not orders_data:
        return {
            "message": "当前账户下暂无订单记录。如有项目需求，可直接描述，我将协助您创建需求单。",
            "orders": []
        }

    user_msg = request.message

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 意图路由：筛选查询 → 详情查询 → 默认列表
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ── 1. 筛选查询 ──
    if _is_filter_query(user_msg):
        # 尝试多种筛选策略
        matched_orders = []
        filter_label = ""

        # 1a. 状态筛选：'哪些还在制作中'
        status_matched = _filter_orders_by_status(user_msg, orders_data)
        if status_matched:
            # 提取用户提到的状态关键词作为标签
            for kw in _STATUS_KW_MAP:
                if kw in user_msg:
                    filter_label = kw
                    break
            matched_orders = status_matched

        # 1b. 否定筛选：'还有哪些没完成的'
        if not matched_orders and re.search(r'(没|未|不是).{0,4}(完成|交付|结束)', user_msg):
            matched_orders = [o for o in orders_data if _get_status_val(o) != "completed"]
            filter_label = "未完成"

        # 1c. 时间范围筛选：'上个月的订单'
        if not matched_orders:
            time_matched = _filter_orders_by_time(user_msg, orders_data)
            if time_matched:
                # 提取时间标签
                for label in ["上个月", "这个月", "本月", "上周", "本周", "这周"]:
                    if label in user_msg:
                        filter_label = label
                        break
                if not filter_label:
                    filter_label = "近期"
                matched_orders = time_matched

        # 1d. 业务字段筛选：'成都的订单怎么样了'
        if not matched_orders:
            keyword = _extract_search_keyword(user_msg)
            if keyword:
                matched_orders = _search_all_matching_orders(user_msg, orders_data)
                filter_label = keyword

        # 输出筛选结果
        if matched_orders:
            summary = _build_order_list_summary(matched_orders)
            overview = _build_status_overview(matched_orders)
            if overview:
                message = f"与「{filter_label}」相关的订单共 {len(matched_orders)} 个，其中{overview}：\n\n{summary}\n\n如需了解某个订单的具体情况，直接告诉我序号或订单号即可。"
            else:
                message = f"与「{filter_label}」相关的订单共 {len(matched_orders)} 个：\n\n{summary}\n\n如需了解某个订单的具体情况，直接告诉我序号或订单号即可。"
            return {"message": message, "orders": matched_orders}
        elif filter_label:
            return {
                "message": f'未找到与「{filter_label}」相关的订单。您可以换个关键词再试，或输入"查看订单"查看全部列表。',
                "orders": []
            }

    # ── 2. 详情查询 ──
    if _is_detail_query(user_msg, request.history):
        matched = (
            _try_match_order_by_order_number(user_msg, orders_data)
            or _try_match_order_by_index(user_msg, orders_data)
            or _try_match_order_by_keyword(user_msg, orders_data)
            or _try_search_order_by_content(user_msg, orders_data)
        )

        if not matched:
            rich_summary = _build_rich_order_summary(orders_data)
            llm_idx = await _llm_match_order(user_msg, request.history, rich_summary)
            if llm_idx and 1 <= llm_idx <= len(orders_data):
                matched = orders_data[llm_idx - 1]

        if matched:
            return {
                "message": _build_order_detail_message(matched),
                "orders": [matched],
                "isDetail": True
            }

        # ── 无法确定具体订单 → 引导用户提供更多信息 ──
        summary = _build_order_list_summary(orders_data)
        return {
            "message": f"抱歉，未能确定您想查看的具体订单。当前共有 {len(orders_data)} 个订单：\n\n{summary}\n\n您可以通过以下方式告诉我：\n- 订单序号（如「第2个」）\n- 订单号（如「ORD-20260418-TZ3K」）\n- 品牌名或城市名（如「耐克的那个」「成都的订单」）",
            "orders": orders_data
        }

    # ── 3. 默认列表展示 ──
    summary = _build_order_list_summary(orders_data)
    overview = _build_status_overview(orders_data)
    if overview:
        intro = f"为您查询到 {len(orders_data)} 个订单，其中{overview}。以下是具体记录："
    else:
        intro = f"为您查询到 {len(orders_data)} 个订单，以下是最近的记录："

    return {
        "message": f"{intro}\n\n{summary}\n\n如需了解某个订单的详情，直接告诉我序号、订单号或相关关键词即可。",
        "orders": orders_data
    }
