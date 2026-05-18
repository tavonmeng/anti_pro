"""公司官网爬取服务

LLM 推测官网 URL → 验证工具检查 → 不对就重试
→ httpx + BeautifulSoup 爬取页面
→ LLM 提取结构化信息（屏幕资源、案例、公司描述）
"""

import re
import json
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from app.config import settings
from app.services.ai_client import post_chat_completion
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger


logger = get_module_logger("ai")

# 子页面关键词 — 用于从首页内链中筛选有价值的页面
_PAGE_KEYWORDS = [
    "媒体", "资源", "屏幕", "大屏", "LED", "媒体矩阵", "媒体资源",
    "案例", "合作案例", "作品", "项目", "案例展示",
    "关于", "about", "公司", "简介", "介绍",
    "产品", "服务", "业务",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 1: LLM 推测 → 验证 → 重试 循环
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def search_company_website(company_name: str, max_retries: int = 3) -> str | None:
    """通过 LLM 推测 + 验证工具 查找公司官网

    流程：
      Round 1: LLM 推测 URL → 验证（访问 + 检查标题/内容是否包含公司名）
      Round 2: 如果验证失败 → 告诉 LLM 上次的 URL 不对及原因 → 重新推测
      Round 3: 最后一次机会

    Args:
        company_name: 公司名称（如 "某某传媒"）
        max_retries: 最大重试次数

    Returns:
        验证通过的官网 URL 或 None
    """
    if not settings.AI_API_KEY:
        log_business_event(logger, "crawl_website_search_skipped", level="warning", company_name=company_name, reason="missing_ai_api_key")
        return None

    # 公司名简化（去掉后缀）
    company_short = (
        company_name
        .replace("有限公司", "").replace("有限责任公司", "")
        .replace("股份", "").replace("集团", "").replace("科技", "")
        .strip()
    )

    feedback_history = []  # 记录每一轮的反馈

    for attempt in range(1, max_retries + 1):
        log_business_event(logger, "crawl_website_guess_started", company_name=company_name, attempt=attempt)

        # 1. LLM 推测 URL
        guessed_urls = await _llm_guess_url(company_name, feedback_history)
        if not guessed_urls:
            log_business_event(logger, "crawl_website_guess_empty", level="warning", company_name=company_name, attempt=attempt)
            feedback_history.append("LLM 无法推测出任何 URL，请尝试更多可能的域名变体")
            continue

        # 2. 逐个验证
        for url in guessed_urls:
            log_business_event(logger, "crawl_website_verify_started", company_name=company_name, attempt=attempt, url=url)
            is_valid, reason = await _verify_website(url, company_name, company_short)

            if is_valid:
                log_business_event(logger, "crawl_website_verified", company_name=company_name, attempt=attempt, url=url)
                return url
            else:
                log_business_event(
                    logger,
                    "crawl_website_verify_failed",
                    level="warning",
                    company_name=company_name,
                    attempt=attempt,
                    url=url,
                    reason=reason,
                )
                feedback_history.append(f"URL {url} 验证失败 — {reason}")

    log_business_event(logger, "crawl_website_not_found", level="warning", company_name=company_name, max_retries=max_retries)
    return None


async def _llm_guess_url(company_name: str, feedback_history: list[str]) -> list[str]:
    """让 LLM 推测公司官网 URL

    Args:
        company_name: 公司全名
        feedback_history: 之前轮次的反馈（哪些 URL 验证失败、失败原因）

    Returns:
        推测的 URL 列表（最多 3 个）
    """
    system_prompt = (
        "你是一个中国企业信息专家，擅长推测中国公司的官方网站域名。\n"
        "用户会给你一个公司名称，你需要推测该公司的官方网站 URL。\n\n"
        "推测规则：\n"
        "1. 中国户外广告/传媒公司通常用拼音、品牌英文名或缩写作为域名\n"
        "2. 常见后缀：.com、.cn、.com.cn\n"
        "3. 举几个已知例子帮助你理解规律：\n"
        "   - 分众传媒 → https://www.focusmedia.cn\n"
        "   - 新潮传媒 → https://www.xinchao.com\n"
        "   - 凤凰都市传媒 → https://www.phoenixmetro.com\n"
        "   - 百灵时代广告 → https://www.bailingad.com\n"
        "   - 华语传媒 → https://www.sinotvmedia.com\n"
        "4. 可以推测多个可能的 URL（最多 3 个），按你认为最可能的排序\n\n"
        "只返回严格的 JSON 数组，不要任何其他文字。\n"
        '例如: ["https://www.example.com", "https://www.example.cn"]'
    )

    user_msg = f"公司名称：{company_name}\n"

    if feedback_history:
        user_msg += "\n以下是之前推测失败的记录，请避免重复并尝试新的可能：\n"
        for fb in feedback_history:
            user_msg += f"  - {fb}\n"

    try:
        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
            },
            timeout=15.0,
        )
        content = data["choices"][0]["message"]["content"].strip()

        # 提取 JSON
        json_match = re.search(r"\[[\s\S]*?\]", content)
        if json_match:
            urls = json.loads(json_match.group(0))
            # 确保是字符串列表且都是 URL
            return [u for u in urls if isinstance(u, str) and u.startswith("http")][:3]
        return []
    except Exception as e:
        log_business_event(logger, "crawl_website_guess_failed", level="warning", company_name=company_name, error=str(e))
        return []


async def _verify_website(url: str, company_name: str, company_short: str) -> tuple[bool, str]:
    """验证 URL 是否是目标公司的官网

    验证策略（多层检查）：
      1. 能否访问（HTTP 200）
      2. 页面标题 <title> 是否包含公司名
      3. 页面正文是否包含公司名
      4. 是否是已知的非官网平台（天眼查、百度百科等）

    Args:
        url: 待验证的 URL
        company_name: 公司全名
        company_short: 公司简称（去掉后缀）

    Returns:
        (is_valid, reason) — 是否验证通过 + 原因描述
    """
    # 0. 过滤已知非官网平台
    blocked_domains = [
        "baidu.com", "tianyancha.com", "qcc.com", "aiqicha.com",
        "zhihu.com", "weibo.com", "douyin.com", "bilibili.com",
        "boss.com", "liepin.com", "zhaopin.com",
    ]
    parsed = urlparse(url)
    if any(d in parsed.netloc for d in blocked_domains):
        return False, f"域名 {parsed.netloc} 是第三方平台，不是公司官网"

    # 1. 尝试访问
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=8.0, verify=False
        ) as client:
            resp = await client.get(url, headers=_HEADERS)

            # 检查状态码
            if resp.status_code >= 400:
                return False, f"HTTP {resp.status_code}，页面无法访问"

            html = resp.text
    except httpx.ConnectError:
        return False, "连接失败，域名可能不存在"
    except httpx.TimeoutException:
        return False, "连接超时，网站可能无法访问"
    except Exception as e:
        return False, f"请求异常: {str(e)[:50]}"

    # 2. 解析 HTML
    soup = BeautifulSoup(html, "html.parser")

    # 3. 检查 <title>
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    title_match = _fuzzy_match(title, company_name, company_short)

    # 4. 检查页面正文（取前 2000 字）
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    body_text = soup.get_text(separator=" ", strip=True)[:2000]
    body_match = _fuzzy_match(body_text, company_name, company_short)

    # 5. 综合判定
    if title_match:
        return True, f"标题匹配: '{title[:50]}'"
    elif body_match:
        # 正文匹配但标题不匹配 — 可能是子页面或改版
        return True, f"正文包含公司名，标题: '{title[:50]}'"
    else:
        # 给出详细失败原因
        snippet = title[:60] if title else "(无标题)"
        body_snippet = body_text[:100] if body_text else "(页面无内容)"
        return False, f"页面标题 '{snippet}' 和正文均不含公司名。正文开头: '{body_snippet}...'"


def _fuzzy_match(text: str, company_name: str, company_short: str) -> bool:
    """模糊匹配：检查文本中是否包含公司名的关键部分

    匹配策略：
      - 完整公司名
      - 简称（去掉后缀）
      - 品牌名核心部分（如 "凤凰都市" 中的 "凤凰都市"）
    """
    if not text:
        return False

    text_lower = text.lower()

    # 完整名匹配
    if company_name in text:
        return True

    # 简称匹配
    if company_short and company_short in text:
        return True

    # 进一步拆分核心词（至少 2 个字的品牌词）
    # 例如 "凤凰都市传媒" → 检查 "凤凰都市"
    core_name = company_short.replace("传媒", "").replace("广告", "").replace("文化", "").strip()
    if core_name and len(core_name) >= 2 and core_name in text:
        return True

    return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 2: 深度爬取
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def crawl_website(base_url: str, max_pages: int = 6) -> str:
    """深度爬取公司官网，返回合并后的纯文本

    策略：爬取首页 + 最多 max_pages-1 个关键子页面

    Args:
        base_url: 官网首页 URL
        max_pages: 最多爬取的页面数量

    Returns:
        合并后的纯文本内容（截断到 8000 字）
    """
    crawled_texts = []
    visited = set()

    # Step 1: 爬取首页
    homepage_text, internal_links = await _crawl_single_page(base_url)
    if homepage_text:
        crawled_texts.append(f"=== 首页 ===\n{homepage_text}")
    visited.add(base_url)

    # Step 2: 从内链中筛选关键子页面
    target_links = _filter_relevant_links(internal_links, base_url)

    # Step 3: 爬取子页面
    for link in target_links[:max_pages - 1]:
        if link in visited:
            continue
        visited.add(link)
        page_text, _ = await _crawl_single_page(link)
        if page_text and len(page_text) > 50:
            crawled_texts.append(f"=== {link} ===\n{page_text}")

    # 合并 & 截断
    full_text = "\n\n".join(crawled_texts)
    if len(full_text) > 8000:
        full_text = full_text[:8000] + "\n...(内容已截断)"

    return full_text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 3: LLM 提取结构化数据
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def extract_company_info(raw_text: str) -> dict:
    """用 LLM 从爬取的网页文本中提取结构化信息

    Returns:
        {
            "description": "公司简介...",
            "advantages": ["优势1", "优势2"],
            "screens": [
                {"city": "成都", "location": "春熙路", "type": "LED大屏", "size": "800㎡", ...},
            ],
            "past_cases": [
                {"title": "某品牌项目", "year": "2025", "city": "成都"},
            ]
        }
    """
    if not settings.AI_API_KEY or not raw_text.strip():
        return {}

    system_prompt = (
        "你是一个数据提取专家。请从以下公司官网内容中提取结构化信息。\n"
        "只返回严格的 JSON，不要任何其他文字。\n\n"
        "需要提取的字段：\n"
        "1. description (string) — 公司简介，一两句话概括\n"
        "2. advantages (list[string]) — 公司核心优势，如'核心商圈资源'、'日均客流30万'\n"
        "3. screens (list[object]) — 屏幕/媒体资源列表，每个包含：\n"
        "   - city: 城市\n"
        "   - location: 具体位置\n"
        "   - type: 屏幕类型（如 L型LED、平面LED、曲面屏等）\n"
        "   - size: 物理尺寸（如 800㎡）\n"
        "   - resolution: 分辨率（如有）\n"
        "   - daily_traffic: 日均客流（如有）\n"
        "4. past_cases (list[object]) — 过往合作案例，每个包含：\n"
        "   - title: 案例标题/项目名\n"
        "   - year: 年份（如有）\n"
        "   - city: 城市（如有）\n"
        "   - brand: 品牌方（如有）\n\n"
        "如果某个字段在网页内容中没有找到对应信息，就设为空列表或空字符串。\n"
        "确保返回合法的 JSON。"
    )

    try:
        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"以下是公司官网的内容：\n\n{raw_text}"},
                ],
            },
            timeout=30.0,
        )
        content = data["choices"][0]["message"]["content"]

        # 尝试从 markdown code block 中提取 JSON
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            content = json_match.group(1)

        return json.loads(content.strip())
    except Exception as e:
        log_business_event(logger, "crawl_extract_failed", level="warning", text_length=len(raw_text or ""), error=str(e))
        return {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 完整流程入口
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def crawl_and_extract(company_name: str) -> dict:
    """完整的 推测 → 验证 → 爬取 → 提取 流程

    Args:
        company_name: 公司名称

    Returns:
        {
            "company_info": {...},
            "screen_resources": [...]
        }
    """
    # Step 1: LLM 推测 + 验证循环
    website_url = await search_company_website(company_name)
    if not website_url:
        log_business_event(logger, "crawl_company_not_found", level="warning", company_name=company_name)
        return {
            "company_info": {
                "name": company_name,
                "crawl_status": "not_found",
            },
            "screen_resources": [],
        }

    # Step 2: 深度爬取
    log_business_event(logger, "crawl_started", company_name=company_name, website_url=website_url)
    raw_text = await crawl_website(website_url)
    if not raw_text or len(raw_text) < 100:
        log_business_event(
            logger,
            "crawl_empty",
            level="warning",
            company_name=company_name,
            website_url=website_url,
            text_length=len(raw_text or ""),
        )
        return {
            "company_info": {
                "name": company_name,
                "website": website_url,
                "crawl_status": "empty",
            },
            "screen_resources": [],
        }

    # Step 3: LLM 提取结构化信息
    extracted = await extract_company_info(raw_text)

    from datetime import datetime

    company_info = {
        "name": company_name,
        "website": website_url,
        "description": extracted.get("description", ""),
        "advantages": extracted.get("advantages", []),
        "past_cases": extracted.get("past_cases", []),
        "crawled_at": datetime.now().isoformat(),
        "crawl_status": "success",
    }

    screen_resources = extracted.get("screens", [])
    log_business_event(
        logger,
        "crawl_completed",
        company_name=company_name,
        website_url=website_url,
        text_length=len(raw_text or ""),
        screen_count=len(screen_resources or []),
        past_case_count=len(company_info.get("past_cases") or []),
    )

    return {
        "company_info": company_info,
        "screen_resources": screen_resources,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 内部工具函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def _crawl_single_page(url: str) -> tuple[str, list[str]]:
    """爬取单个页面，返回 (纯文本, 内链列表)"""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=10.0, verify=False
        ) as client:
            resp = await client.get(url, headers=_HEADERS)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # 提取内链
        internal_links = []
        parsed_base = urlparse(url)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(url, href)
            parsed = urlparse(full_url)
            if parsed.netloc == parsed_base.netloc and parsed.scheme in ("http", "https"):
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if clean_url not in internal_links:
                    internal_links.append(clean_url)

        # 清洗 HTML → 纯文本
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # 去除连续空行
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text, internal_links

    except Exception as e:
        log_business_event(logger, "crawl_page_failed", level="warning", url=url, error=str(e))
        return "", []


def _filter_relevant_links(links: list[str], base_url: str) -> list[str]:
    """从内链中筛选包含关键词的有价值页面"""
    scored_links = []
    for link in links:
        if link == base_url:
            continue
        path = urlparse(link).path.lower()
        score = sum(1 for kw in _PAGE_KEYWORDS if kw in path)
        if score > 0:
            scored_links.append((score, link))

    # 按得分排序
    scored_links.sort(key=lambda x: x[0], reverse=True)
    return [link for _, link in scored_links]
