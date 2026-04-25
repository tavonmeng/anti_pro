"""
订单查询 Agent — 独立模块
负责订单的智能查询、筛选、详情展示、状态概览等全部能力。
"""

import re
import httpx
from datetime import datetime, timedelta
from typing import Optional
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
    "draft": "草稿", "pending_assign": "待分配", "pending_contract": "合同与付款",
    "in_production": "制作中",
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
    "待分配": "pending_assign", "合同": "pending_contract", "付款": "pending_contract",
    "签合同": "pending_contract", "首付": "pending_contract", "预付": "pending_contract", "合同与付款": "pending_contract",
    "制作中": "in_production",
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

# 提取搜索关键词时需要过滤掉的噪音词（按长度从长到短排列，避免短词先破坏长词）
_NOISE_WORDS = sorted([
    "看一下", "看下", "列出", "展示", "显示", "查看", "搜索", "查询", "获取", "告诉我", "给我", "帮我",
    "订单", "单子", "的那个", "那个", "这个", "帮我看", "帮我查", "一下",
    "看看", "查查", "查一下", "找一下", "找找", "关于", "有关",
    "想看", "想查", "具体", "详情", "详细",
    "有几个", "有多少", "有哪些", "都有哪些", "都有什么",
    "是不是", "有好几个", "有没有", "是否",
    "所有", "全部", "一共", "多少",
    "我的",
    "怎么样了", "怎么样", "什么情况", "进展如何", "进展怎样",
    "进展", "进度", "到哪一步了", "到哪一步", "到什么阶段",
    "什么状态", "还好吗", "顺利吗",
    "还有", "哪些", "没有",
    "还在", "正在", "目前", "现在",
    "上个月", "这个月", "最近", "本周", "上周",
], key=len, reverse=True)


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
    """从用户消息中提取业务搜索关键词

    策略：先移除多字噪音短语（已按长度降序排列），再清理残留的
    单字虚词（的、了、请等），但仅当结果长度 > 1 时才做单字清理，
    避免把"成都"这类关键词拆碎。
    """
    clean_msg = user_msg
    # 移除多字噪音词（长词优先）
    for w in _NOISE_WORDS:
        clean_msg = clean_msg.replace(w, "")
    clean_msg = clean_msg.strip()

    # 只在结果仍然较长时，才尝试清理单字虚词
    if len(clean_msg) > 1:
        for ch in ["的", "了", "请", "吗", "呢"]:
            clean_msg = clean_msg.replace(ch, "")
    return clean_msg.strip()


# ───────────────────────────────────────────────────────
# 匹配策略
# ───────────────────────────────────────────────────────

def _try_match_order_by_index(user_msg: str, orders: list) -> Optional[dict]:
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


def _try_match_order_by_order_number(user_msg: str, orders: list) -> Optional[dict]:
    """通过订单号精确匹配，如 'ORD-20260418-TZ3K'"""
    m = re.search(r'(ORD-\d{8}-[A-Z0-9]{4})', user_msg, re.IGNORECASE)
    if m:
        target = m.group(1).upper()
        for o in orders:
            if _get_order_num(o).upper() == target:
                return o
    return None


def _try_match_order_by_keyword(user_msg: str, orders: list) -> Optional[dict]:
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


def _try_search_order_by_content(user_msg: str, orders: list) -> Optional[dict]:
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
        "pending_contract": f"{ref}项目已确认需求，目前处于合同签订与首付款确认阶段，待合同流程完成后将正式进入制作流程。",
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

    priority = ["制作中", "待审核", "需修改", "合同与付款", "待分配", "初稿就绪", "终稿就绪", "审核驳回", "已完成", "草稿"]
    parts = [f"{counts[s]}个{s}" for s in priority if counts.get(s, 0) > 0]
    for s, c in counts.items():
        if s not in priority and c > 0:
            parts.append(f"{c}个{s}")
    return "、".join(parts)


# ───────────────────────────────────────────────────────
# LLM 智能理解（替代正则意图检测）
# ───────────────────────────────────────────────────────

async def _llm_understand_query(user_msg: str, history: list, orders_summary: str) -> Optional[dict]:
    """使用 LLM 一次性完成意图分类 + 参数提取，返回结构化 JSON。

    返回示例：
      {"intent": "detail", "match_indices": [2]}
      {"intent": "filter", "match_indices": [1, 3, 5], "label": "成都"}
      {"intent": "list_all"}
    """
    if not settings.AI_API_KEY:
        return None

    try:
        prompt = (
            "你是一个订单查询意图分析器。根据用户消息、对话历史和订单列表，输出严格 JSON。\n\n"
            f"当前订单列表：\n{orders_summary}\n\n"
            "【任务】分析用户想做什么，返回 JSON（不要返回任何其他内容）：\n\n"
            "1. 如果用户想查看某个特定订单的详情（例如通过序号、订单号指定，或提到了能对应唯一记录的品牌/城市）：\n"
            '   返回 {"intent": "detail", "match_indices": [序号], "label": "匹配关键词"}\n\n'
            "2. 如果用户想筛选/查看多个订单，请尝试捕捉用户想匹配的【数据库业务字段】，目前支持的维度有：\n"
            "   - 业务类型：如裸眼3D、数字艺术\n"
            "   - 订单状态：如草稿、合同与付款、制作中、审核、完成\n"
            "   - 客户属性：品牌(brand)、城市(city)、风格(style)\n"
            "   - 时间范围：如上个月、本周等\n"
            '   遇到这几类描述时进行多项匹配，返回 {"intent": "filter", "match_indices": [匹配的序号列表], "label": "筛选条件描述"}\n\n'
            "3. 如果用户想查看所有订单概览，没有特定筛选条件（仅要求看订单）：\n"
            '   返回 {"intent": "list_all"}\n\n'
            "4. 如果用户的消息根本不是在查询订单（比如闲聊、问其他问题）：\n"
            '   返回 {"intent": "not_order_query"}\n\n'
            "【规则】\n"
            "- match_indices 使用订单列表中的序号（从1开始）\n"
            "- 当用户提到上述【业务字段】（如城市是成都，品牌是耐克，状态是制作中）时，要精确对照当前列表数据。\n"
            "- 一个条件匹配到多个订单时，全部列入 match_indices\n"
            "- 用户的模糊化描述需要与业务字段对齐（例如：'还没完工的' -> 匹配非completed状态的订单）\n"
            "- 结合对话历史理解上下文（如用户之前看到了列表，现在说'第2个'）\n"
            "- 只输出 JSON，不要输出任何其他文字"
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
                    "max_tokens": 200,
                    "temperature": 0,
                    "response_format": {"type": "json_object"}
                },
                timeout=15.0
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            # 兼容 markdown 包裹
            if raw.startswith("```"):
                raw = raw.split("```json")[-1].split("```")[0].strip() if "```json" in raw else raw.split("```")[1].split("```")[0].strip()
            import json as _json
            return _json.loads(raw)
    except Exception as e:
        print(f"LLM 订单意图分析失败: {e}")
    return None


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
    # LLM 智能意图路由
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    rich_summary = _build_rich_order_summary(orders_data)
    llm_result = await _llm_understand_query(user_msg, request.history, rich_summary)

    intent = (llm_result or {}).get("intent", "list_all")
    match_indices = (llm_result or {}).get("match_indices", [])
    label = (llm_result or {}).get("label", "")

    # ── 1. 详情查询：LLM 判定用户想查看某个特定订单 ──
    if intent == "detail" and match_indices:
        idx = match_indices[0]
        if 1 <= idx <= len(orders_data):
            matched = orders_data[idx - 1]
            return {
                "message": _build_order_detail_message(matched),
                "orders": [matched],
                "isDetail": True
            }

    # ── 2. 筛选查询：LLM 判定用户想按条件筛选多个订单 ──
    if intent == "filter":
        matched_orders = [orders_data[i - 1] for i in match_indices if 1 <= i <= len(orders_data)]
        if matched_orders:
            summary = _build_order_list_summary(matched_orders)
            overview = _build_status_overview(matched_orders)
            filter_label = label or "筛选结果"
            if overview:
                message = f"与「{filter_label}」相关的订单共 {len(matched_orders)} 个，其中{overview}：\n\n{summary}\n\n如需了解某个订单的具体情况，直接告诉我序号或订单号即可。"
            else:
                message = f"与「{filter_label}」相关的订单共 {len(matched_orders)} 个：\n\n{summary}\n\n如需了解某个订单的具体情况，直接告诉我序号或订单号即可。"
            return {"message": message, "orders": matched_orders}
        else:
            filter_label = label or "该条件"
            return {
                "message": f'未找到与「{filter_label}」相关的订单。您可以换个关键词再试，或输入"查看订单"查看全部列表。',
                "orders": []
            }

    # ── 3. 非订单查询：LLM 判定用户不是在查询订单 ──
    if intent == "not_order_query":
        return {
            "message": "这个问题似乎不是关于订单查询的。如需查看订单，可以告诉我'查看我的订单'或提供订单号、品牌名等关键词。",
            "orders": []
        }

    # ── 4. 默认列表展示 ──
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
