"""PDF 生成服务 - 订单需求确认函 / 订单确认函"""

import io
import os
import platform
from datetime import datetime, timedelta
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger
from app.utils.timezone import beijing_now, ensure_beijing


logger = get_module_logger("order")


def _get_pdf_logo_path() -> str:
    """返回 PDF 可用的官方 logo 图片路径。"""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "official-mark-black.png")


def _draw_confirmation_watermark(canvas, doc):
    """在确认函页面底层绘制左右两侧的低透明度品牌水印。"""
    logo_path = _get_pdf_logo_path()
    if not os.path.exists(logo_path):
        return

    # 避免在不支持透明度的 ReportLab 版本里画出过重的黑色背景。
    if not hasattr(canvas, "setFillAlpha"):
        return

    page_width, page_height = A4
    watermark_height = 340 * mm
    watermark_width = watermark_height * (466 / 831)
    watermark_y = (page_height - watermark_height) / 2
    watermark_alpha = 0.045
    visible_width = watermark_width / 2

    def draw_logo(image_x: float, flip_vertical: bool = False):
        canvas.saveState()
        canvas.setFillAlpha(watermark_alpha)
        canvas.setStrokeAlpha(watermark_alpha)
        if flip_vertical:
            canvas.translate(image_x, watermark_y + watermark_height)
            canvas.scale(1, -1)
            canvas.drawImage(
                logo_path,
                0,
                0,
                width=watermark_width,
                height=watermark_height,
                mask="auto",
            )
        else:
            canvas.drawImage(
                logo_path,
                image_x,
                watermark_y,
                width=watermark_width,
                height=watermark_height,
                mask="auto",
            )
        canvas.restoreState()

    draw_logo(-(watermark_width - visible_width), flip_vertical=True)
    draw_logo(page_width - visible_width, flip_vertical=False)


# ========== 中文字体注册 ==========

def _try_register_ttfont(font_path: str, font_name: str = "Chinese") -> bool:
    """尝试注册一个 TTF/TTC 字体文件，返回是否成功"""
    if not os.path.exists(font_path):
        return False
    try:
        if font_path.lower().endswith('.ttc'):
            # TTC 文件必须指定 subfontIndex，否则某些系统上会随机失败
            pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=0))
        else:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        return True
    except Exception:
        return False


def _find_linux_cjk_font_via_fc() -> str:
    """通过 fc-list 命令动态查找系统中的任意 CJK 字体文件"""
    import subprocess
    try:
        result = subprocess.run(
            ['fc-list', ':lang=zh', '-f', '%{file}\n'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            # 返回第一个找到的字体文件路径
            for line in result.stdout.strip().split('\n'):
                path = line.strip()
                if path and os.path.exists(path):
                    return path
    except Exception:
        pass
    return ""


def _register_chinese_fonts():
    """
    注册中文字体（多层容错）：
    1. 优先尝试常见系统字体路径（包含 .ttc subfontIndex 修复）
    2. 通过 fc-list 动态查找任意已安装的 CJK 字体
    3. 使用 ReportLab 内置 CID 字体（STSong-Light）作为终极后备
    """
    system = platform.system()
    
    # 第一层：常见系统字体路径
    font_paths = {
        "Darwin": [  # macOS
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ],
        "Linux": [
            # wqy 系列（最常见的 Linux 中文字体）
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc",
            "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
            # Noto CJK 系列
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc",
            # Droid 系列
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            "/usr/share/fonts/droid/DroidSansFallbackFull.ttf",
            # 通用路径（阿里云 Alibaba Cloud Linux）
            "/usr/share/fonts/chinese/TrueType/simhei.ttf",
            "/usr/share/fonts/chinese/TrueType/simsun.ttc",
        ],
        "Windows": [
            "C:\\Windows\\Fonts\\msyh.ttc",
            "C:\\Windows\\Fonts\\simhei.ttf",
            "C:\\Windows\\Fonts\\simsun.ttc",
        ]
    }
    
    candidates = font_paths.get(system, [])
    
    for path in candidates:
        if _try_register_ttfont(path, "Chinese"):
            _try_register_ttfont(path, "ChineseBold")
            log_business_event(logger, "pdf_font_registered", font_type="ttf", font_path=path)
            return "ttf"
    
    # 第二层：通过 fc-list 动态查找（仅 Linux）
    if system == "Linux":
        fc_path = _find_linux_cjk_font_via_fc()
        if fc_path:
            if _try_register_ttfont(fc_path, "Chinese"):
                _try_register_ttfont(fc_path, "ChineseBold")
                log_business_event(logger, "pdf_font_registered", font_type="ttf", font_path=fc_path, source="fc-list")
                return "ttf"
    
    # 第三层：使用 ReportLab 内置 CID 字体（不需要任何外部文件）
    try:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        log_business_event(logger, "pdf_font_registered", font_type="cid", font_name="STSong-Light")
        return "cid"
    except Exception:
        pass
    
    # 全部失败
    log_business_event(logger, "pdf_font_missing", level="warning")
    return "none"


_FONT_TYPE = _register_chinese_fonts()

if _FONT_TYPE == "ttf":
    _FONT = "Chinese"
    _FONT_BOLD = "ChineseBold"
elif _FONT_TYPE == "cid":
    _FONT = "STSong-Light"
    _FONT_BOLD = "STSong-Light"  # CID 字体没有 Bold 变体
else:
    _FONT = "Helvetica"
    _FONT_BOLD = "Helvetica-Bold"


# ========== 样式定义 ==========

def _get_styles():
    """获取 PDF 样式集合"""
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name="DocTitle",
        fontName=_FONT_BOLD,
        fontSize=22,
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=6,
        textColor=colors.HexColor("#1a1c1c"),
    ))
    
    styles.add(ParagraphStyle(
        name="DocSubtitle",
        fontName=_FONT,
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        spaceAfter=16,
        textColor=colors.HexColor("#86868b"),
    ))
    
    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontName=_FONT_BOLD,
        fontSize=13,
        leading=18,
        spaceBefore=16,
        spaceAfter=8,
        textColor=colors.HexColor("#1a1c1c"),
        borderPadding=(0, 0, 0, 8),
    ))
    
    styles.add(ParagraphStyle(
        name="BodyCN",
        fontName=_FONT,
        fontSize=10,
        leading=16,
        spaceAfter=4,
        textColor=colors.HexColor("#414754"),
    ))
    
    styles.add(ParagraphStyle(
        name="BodyCNBold",
        fontName=_FONT_BOLD,
        fontSize=10,
        leading=16,
        spaceAfter=4,
        textColor=colors.HexColor("#1a1c1c"),
    ))
    
    styles.add(ParagraphStyle(
        name="SmallNote",
        fontName=_FONT,
        fontSize=8,
        leading=12,
        textColor=colors.HexColor("#86868b"),
    ))
    
    styles.add(ParagraphStyle(
        name="Footer",
        fontName=_FONT,
        fontSize=8,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#aaaaaa"),
    ))
    
    return styles


# ========== 文本映射 ==========

ORDER_TYPE_MAP = {
    "video_purchase": "3D OOH数字内容资源库",
    "ai_3d_custom": "AI驱动3D OOH内容定制",
    "digital_art": "数字艺术与沉浸式视觉设计",
}

STATUS_MAP = {
    "draft": "订单草稿",
    "pending_assign": "待分配",
    "pending_contract": "合同与付款",
    "in_production": "制作中",
    "pending_review": "待审核",
    "preview_ready": "初稿预览",
    "review_rejected": "审核拒绝",
    "revision_needed": "需要修改",
    "final_preview": "终稿预览",
    "completed": "已完成",
    "cancelled": "已取消",
}


# ========== 辅助方法 ==========

def _format_time(time_str: str) -> str:
    """格式化时间为北京时间"""
    if not time_str:
        return "-"
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        beijing = ensure_beijing(dt)
        return beijing.strftime("%Y年%m月%d日 %H:%M")
    except Exception:
        return time_str


def _pdf_paragraph_text(value) -> str:
    """Escape arbitrary user text for ReportLab Paragraph and preserve line breaks."""
    text = escape(str(value or ""))
    return text.replace("\n", "<br/>")


def _build_summary_rows(order_data: dict, order_type: str) -> list:
    """根据订单类型构建摘要行"""
    rows = []
    
    if order_type == "video_purchase":
        industry_map = {"movie": "电影", "outdoor": "户外", "custom": order_data.get("customIndustry", "自定义")}
        style_map = {"scifi": "科幻", "realistic": "写真", "custom": order_data.get("customStyle", "自定义")}
        
        rows.append(("行业类型", industry_map.get(order_data.get("industryType", ""), order_data.get("industryType", "-"))))
        rows.append(("视觉风格", style_map.get(order_data.get("visualStyle", ""), order_data.get("visualStyle", "-"))))
        if order_data.get("duration"):
            rows.append(("时长", f"{order_data['duration']} 秒"))
        pr = order_data.get("priceRange", {})
        if pr:
            rows.append(("价格区间", f"¥{pr.get('min', 0)} - ¥{pr.get('max', 0)}"))
        if order_data.get("resolution"):
            rows.append(("分辨率", order_data["resolution"]))
        if order_data.get("size"):
            rows.append(("屏幕尺寸", order_data["size"]))
        if order_data.get("curvature"):
            rows.append(("曲率", order_data["curvature"]))
    
    elif order_type == "ai_3d_custom":
        # 检测是否为媒体方订单（通过 project_name 字段判断）
        is_media = bool(order_data.get("project_name"))
        if is_media:
            field_map = [
                ("project_name", "项目名称"),
                ("resource_background", "项目背景 & 媒体简介"),
                ("audience_scene", "目标受众 & 场景特点"),
                ("city_location", "投放城市 & 媒体位置"),
                ("viewing_path", "观看动线说明"),
                ("art_direction", "艺术方向 & 风格偏好"),
                ("theme_concept", "内容主题 & 核心表达"),
                ("media_specs", "媒体尺寸 & 物理规格"),
                ("tech_delivery", "技术需求"),
                ("content_review", "素材审核规范 & 周期"),
                ("media_positioning", "媒体定位 & 品牌调性"),
                ("timing_number", "投放时长 & 数量"),
                ("budget", "项目制作预算"),
                ("online_time", "预计上刊时间"),
                ("special_requirements", "其他特殊合作要求"),
                ("remarks", "备注"),
            ]
        else:
            field_map = [
                ("brand", "品牌与产品关键词"),
                ("target_group", "目标受众"),
                ("brand_tone", "品牌调性"),
                ("style", "风格偏好"),
                ("city", "投放城市/站点"),
                ("media_size", "投放媒体尺寸"),
                ("time_number", "投放时长数量"),
                ("technology", "技术需求"),
                ("budget", "制作预算"),
                ("online_time", "预计上刊时间"),
                ("sales_contact", "销售对接人"),
            ]
        for key, label in field_map:
            val = order_data.get(key)
            if val:
                rows.append((label, str(val)[:100]))
        
        if not is_media:
            if order_data.get("background"):
                rows.append(("项目背景", order_data["background"][:100]))
            if order_data.get("content"):
                rows.append(("内容需求", order_data["content"][:100]))
            if order_data.get("prohibited_content"):
                rows.append(("品牌禁忌", order_data["prohibited_content"][:100]))
        photos = order_data.get("scenePhotos", [])
        if photos:
            rows.append(("现场实拍图", f"{len(photos)} 张"))
    
    elif order_type == "digital_art":
        art_map = {"abstract": "抽象", "realistic": "写实", "installation": "装置", "dynamic": "动态艺术", "custom": order_data.get("customDirection", "自定义")}
        rows.append(("艺术方向", art_map.get(order_data.get("artDirection", ""), order_data.get("artDirection", "-"))))
        if order_data.get("description"):
            rows.append(("说明文字", order_data["description"][:100]))
        materials = order_data.get("materials", [])
        if materials:
            rows.append(("相关材料", f"{len(materials)} 个文件"))
    
    return rows


def _build_screen_description(order_type: str, order_data: dict) -> str:
    """根据订单数据构建投放屏幕描述

    优先使用 media_specs（媒体方订单）中的信息，
    回退到 media_size、size 等字段。
    
    Returns:
        如 "长虹P5户外全彩LED显示屏" 或 "户外大屏"
    """
    media_specs = order_data.get("media_specs", "")
    tech_delivery = order_data.get("tech_delivery", "")
    
    if order_type == "ai_3d_custom":
        # 媒体方订单：尝试从 media_specs 提取屏幕名称
        if media_specs:
            # media_specs 通常包含完整的屏幕描述，直接使用
            # 截取前 50 字符作为简称
            return media_specs[:50]
        
        # 品牌方订单：使用 media_size
        media_size = order_data.get("media_size", "")
        if media_size:
            return media_size[:50]
        
        return "户外大屏"
    
    elif order_type == "video_purchase":
        size = order_data.get("size", "")
        if size:
            return f"{size}户外屏"
        return "户外大屏"
    
    elif order_type == "digital_art":
        return "数字艺术展示屏"
    
    return ""


# ========== 核心 PDF 生成方法 ==========

class PDFService:
    """PDF 生成服务"""

    @staticmethod
    def generate_order_confirmation_pdf(order_dict: dict) -> bytes:
        """
        生成内容制作确认函 PDF。
        
        根据订单类型和用户注册信息，自动填充：
        - 企业名称（来自用户注册信息）
        - 投放屏幕/媒体信息（来自订单数据）
        - 预算、时长、尺寸、分辨率（来自订单数据）
        - 制作周期和交付日期（自动计算）
        
        参数:
            order_dict: 与 _build_order_response 返回格式一致的订单字典
        
        返回:
            PDF 文件的 bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=25 * mm,
            bottomMargin=20 * mm,
            leftMargin=25 * mm,
            rightMargin=25 * mm,
        )
        
        styles = _get_styles()
        elements = []
        
        order_number = order_dict.get("orderNumber", "N/A")
        order_type = order_dict.get("orderType", "")
        # 注意: _build_order_response 将 order.order_data 合并到了顶层
        # 所以 project_name, media_specs 等字段直接在 order_dict 上
        order_data = order_dict
        created_at_str = order_dict.get("createdAt", "")
        
        # 用户信息
        enterprise_name = order_dict.get("userEnterprise") or order_dict.get("userName", "-")
        
        # 根据订单类型生成标题
        title_map = {
            "ai_3d_custom": "户外大屏裸眼3D内容制作确认函",
            "video_purchase": "3D OOH数字内容资源库确认函",
            "digital_art": "数字艺术与沉浸式视觉设计确认函",
        }
        doc_title = title_map.get(order_type, "内容制作确认函")
        
        # 制作周期
        prod_days_map = {"video_purchase": 5, "ai_3d_custom": 15, "digital_art": 7}
        prod_days = prod_days_map.get(order_type, 15)
        
        # 计算关键日期
        try:
            start_dt = ensure_beijing(datetime.fromisoformat(created_at_str.replace("Z", "+00:00")))
        except Exception:
            start_dt = beijing_now()
        
        start_date_str = start_dt.strftime("%Y年%m月%d日")
        
        # 计算交付日期（跳过周末的简化计算：工作日 ≈ 自然日 * 1.4）
        delivery_delta = timedelta(days=int(prod_days * 1.4))
        delivery_dt = start_dt + delivery_delta
        delivery_date_str = delivery_dt.strftime("%Y年%m月%d日")
        
        # ========== 从订单数据中提取关键信息 ==========
        
        # 媒体方订单（ai_3d_custom）的字段
        project_name = order_data.get("project_name", "")
        media_specs = order_data.get("media_specs", "")         # 媒体尺寸 & 物理规格
        tech_delivery = order_data.get("tech_delivery", "")     # 技术需求
        budget = order_data.get("budget", "")                   # 预算
        timing_number = order_data.get("timing_number", "")     # 投放时长 & 数量
        city_location = order_data.get("city_location", "")     # 投放城市 & 媒体位置
        online_time = order_data.get("online_time", "")         # 预计上刊时间
        art_direction = order_data.get("art_direction", "")     # 艺术方向
        theme_concept = order_data.get("theme_concept", "")     # 主题 & 核心表达
        resource_bg = order_data.get("resource_background", "") # 项目背景
        
        # 品牌方订单（旧 ai_3d_custom）
        brand = order_data.get("brand", "")
        media_size = order_data.get("media_size", "")
        city = order_data.get("city", "")
        
        # video_purchase 字段
        duration = order_data.get("duration", "")
        resolution = order_data.get("resolution", "")
        size = order_data.get("size", "")
        
        # 构建「投放屏幕」描述
        screen_desc = _build_screen_description(order_type, order_data)
        
        # ========== 开始构建 PDF ==========
        
        logo_path = _get_pdf_logo_path()
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=11 * mm, height=20 * mm)
            logo.hAlign = "CENTER"
            elements.append(logo)
            elements.append(Spacer(1, 5))

        # ---- 标题 ----
        elements.append(Paragraph(doc_title, styles["DocTitle"]))
        elements.append(Paragraph(f"编号：{order_number}", styles["DocSubtitle"]))
        elements.append(HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.HexColor("#e0e0e0"),
            spaceAfter=14,
        ))
        
        # ---- 致辞 ----
        salutation = f"致<b>{enterprise_name}</b>："
        elements.append(Paragraph(salutation, styles["BodyCNBold"]))
        elements.append(Spacer(1, 6))
        
        # ---- 开场段 ----
        opening = (
            f"&nbsp;&nbsp;&nbsp;&nbsp;贵司与我司（北京数艺光程数字科技有限责任公司）就"
        )
        # 根据订单类型拼接合作描述
        if order_type == "ai_3d_custom":
            if screen_desc:
                opening += f"<b>{screen_desc}</b>裸眼3D视频制作事宜，"
            else:
                opening += "户外大屏裸眼3D视频制作事宜，"
        elif order_type == "video_purchase":
            opening += "3D OOH数字内容资源库事宜，"
        elif order_type == "digital_art":
            opening += "数字艺术与沉浸式视觉设计事宜，"
        else:
            opening += "内容制作事宜，"
        opening += "经过初步协商，双方达成如下合作："
        elements.append(Paragraph(opening, styles["BodyCN"]))
        elements.append(Spacer(1, 10))
        
        # ---- 一、项目基本情况 ----
        elements.append(Paragraph("一、项目基本情况", styles["SectionTitle"]))
        
        project_rows = []
        
        # 项目名称
        if project_name:
            project_rows.append(("项目名称", project_name))
        elif brand:
            project_rows.append(("品牌/产品", brand))
        
        # 全片时长
        if timing_number:
            project_rows.append(("投放时长/数量", timing_number))
        elif duration:
            project_rows.append(("全片时长", f"{duration}秒"))
        
        # 投放屏幕
        if screen_desc:
            project_rows.append(("投放屏幕", screen_desc))
        
        # 执行预算
        if budget:
            project_rows.append(("执行预算", budget))
        
        # 屏幕尺寸 & 物理规格
        if media_specs:
            project_rows.append(("媒体尺寸/物理规格", media_specs))
        elif size:
            project_rows.append(("屏幕尺寸", size))
        
        # 技术需求（分辨率等）
        if tech_delivery:
            project_rows.append(("技术需求", tech_delivery))
        elif resolution:
            project_rows.append(("屏幕分辨率", resolution))
        
        # 投放城市
        if city_location:
            project_rows.append(("投放城市/位置", city_location))
        elif city:
            project_rows.append(("投放城市", city))
        
        # 艺术方向
        if art_direction:
            project_rows.append(("艺术方向/风格", art_direction))
        
        # 主题
        if theme_concept:
            project_rows.append(("内容主题", theme_concept))
        
        if project_rows:
            # 使用 Paragraph 包裹长文本，避免表格溢出
            wrapped_rows = []
            for label, value in project_rows:
                label_p = Paragraph(str(label), ParagraphStyle(
                    "CellLabel", fontName=_FONT, fontSize=10, leading=14,
                    textColor=colors.HexColor("#86868b"),
                ))
                value_p = Paragraph(str(value)[:200], ParagraphStyle(
                    "CellValue", fontName=_FONT_BOLD, fontSize=10, leading=14,
                    textColor=colors.HexColor("#1a1c1c"),
                ))
                wrapped_rows.append([label_p, value_p])
            
            project_table = Table(wrapped_rows, colWidths=[120, 340])
            project_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fafafa")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e8e8e8")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]))
            elements.append(project_table)
        
        elements.append(Spacer(1, 8))
        
        # 合作确认语句
        cooperation_stmt = (
            f"&nbsp;&nbsp;&nbsp;&nbsp;双方展开商务合作，确认于"
            f"<b>{start_date_str}</b>进入三维制作阶段。"
        )
        elements.append(Paragraph(cooperation_stmt, styles["BodyCN"]))
        elements.append(Spacer(1, 10))
        
        # ---- 二、制作周期与交付 ----
        elements.append(Paragraph("二、制作周期与交付", styles["SectionTitle"]))
        
        delivery_text = (
            f"&nbsp;&nbsp;&nbsp;&nbsp;因制作周期紧张，乙方需于"
            f"<b>{delivery_date_str}</b>前（{prod_days}个工作日内）"
            f"输出项目成片且同步给甲方，双方合同于项目开工后同步推进并于项目交付前签署。"
            f"故双方就本次合作形成如上约定。"
        )
        elements.append(Paragraph(delivery_text, styles["BodyCN"]))
        elements.append(Spacer(1, 10))
        
        # ---- 三、补充说明 ----
        elements.append(Paragraph("三、补充说明", styles["SectionTitle"]))
        
        supplement = (
            "&nbsp;&nbsp;&nbsp;&nbsp;具体合作细则以双方的正式合同为准。"
        )
        elements.append(Paragraph(supplement, styles["BodyCN"]))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(
            f"&nbsp;&nbsp;&nbsp;&nbsp;甲方：<b>{enterprise_name}</b>",
            styles["BodyCN"]
        ))
        elements.append(Paragraph(
            "&nbsp;&nbsp;&nbsp;&nbsp;乙方：<b>北京数艺光程数字科技有限责任公司</b>",
            styles["BodyCN"]
        ))
        
        elements.append(Spacer(1, 16))
        
        # ---- 分隔线 ----
        elements.append(HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.HexColor("#e0e0e0"),
            spaceBefore=8,
            spaceAfter=12,
        ))
        
        elements.append(Spacer(1, 20))
        
        # ---- 右下角：公司名 + 日期 ----
        right_style = ParagraphStyle(
            "RightAlign", fontName=_FONT_BOLD, fontSize=10, leading=16,
            alignment=TA_RIGHT, textColor=colors.HexColor("#1a1c1c"),
        )
        elements.append(Paragraph("北京数艺光程数字科技有限责任公司", right_style))
        elements.append(Paragraph(start_date_str, right_style))
        
        elements.append(Spacer(1, 20))
        
        # ---- 页脚 ----
        elements.append(HRFlowable(
            width="100%",
            thickness=0.3,
            color=colors.HexColor("#d0d0d0"),
            spaceAfter=8,
        ))
        
        now_beijing = beijing_now()
        elements.append(Paragraph(
            f"北京数艺光程数字科技有限责任公司 · 本文件由系统自动生成 · {now_beijing.strftime('%Y-%m-%d %H:%M')}",
            styles["Footer"]
        ))
        
        # 构建 PDF
        doc.build(
            elements,
            onFirstPage=_draw_confirmation_watermark,
            onLaterPages=_draw_confirmation_watermark,
        )
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    @staticmethod
    def generate_order_detail_pdf(order_dict: dict) -> bytes:
        """
        生成订单详细信息 PDF（管理员格式化版本，包含更多信息）。
        
        参数:
            order_dict: 与 _build_order_response 返回格式一致的订单字典
        
        返回:
            PDF 文件的 bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=20 * mm,
            bottomMargin=18 * mm,
            leftMargin=22 * mm,
            rightMargin=22 * mm,
        )
        
        styles = _get_styles()
        elements = []
        
        order_number = order_dict.get("orderNumber", "N/A")
        order_type = order_dict.get("orderType", "")
        order_type_text = ORDER_TYPE_MAP.get(order_type, order_type)
        order_data = order_dict.get("orderData", {})
        status = order_dict.get("status", "")
        status_text = STATUS_MAP.get(status, status)
        user_name = order_dict.get("userName", "-")
        created_at = _format_time(order_dict.get("createdAt", ""))
        updated_at = _format_time(order_dict.get("updatedAt", ""))
        revision_count = order_dict.get("revisionCount", 0)
        
        # ---- 标题 ----
        elements.append(Paragraph("订单详情报告", styles["DocTitle"]))
        elements.append(Paragraph(f"【内部文件】{order_number}", styles["DocSubtitle"]))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0071e3"), spaceAfter=12))
        
        # ---- 基本信息 ----
        elements.append(Paragraph("一、订单基本信息", styles["SectionTitle"]))
        
        basic_data = [
            ["订单编号", order_number, "订单类型", order_type_text],
            ["当前状态", status_text, "修改次数", f"{revision_count} 次"],
            ["提交用户", user_name, "创建时间", created_at],
            ["最后更新", updated_at, "", ""],
        ]
        
        assignees = order_dict.get("assignees", [])
        if assignees:
            names = ", ".join([a.get("name", "") for a in assignees])
            basic_data.append(["负责人", names, "", ""])
        
        basic_table = Table(basic_data, colWidths=[80, 150, 80, 150])
        basic_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), _FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#86868b")),
            ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#86868b")),
            ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1a1c1c")),
            ("TEXTCOLOR", (3, 0), (3, -1), colors.HexColor("#1a1c1c")),
            ("FONTNAME", (1, 0), (1, -1), _FONT_BOLD),
            ("FONTNAME", (3, 0), (3, -1), _FONT_BOLD),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f5f7")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f5f5f7")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(basic_table)
        elements.append(Spacer(1, 12))
        
        # ---- 需求明细 ----
        elements.append(Paragraph("二、需求明细", styles["SectionTitle"]))
        
        summary_rows = _build_summary_rows(order_data, order_type)
        if summary_rows:
            label_style = ParagraphStyle(
                "DetailSummaryLabel",
                fontName=_FONT,
                fontSize=9,
                leading=13,
                textColor=colors.HexColor("#86868b"),
            )
            value_style = ParagraphStyle(
                "DetailSummaryValue",
                fontName=_FONT,
                fontSize=9,
                leading=13,
                textColor=colors.HexColor("#1a1c1c"),
            )
            wrapped_summary_rows = [
                [
                    Paragraph(_pdf_paragraph_text(label), label_style),
                    Paragraph(_pdf_paragraph_text(value), value_style),
                ]
                for label, value in summary_rows
            ]

            summary_table = Table(wrapped_summary_rows, colWidths=[120, 340])
            summary_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), _FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#86868b")),
                ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1a1c1c")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f5f7")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            elements.append(summary_table)
        else:
            elements.append(Paragraph("暂无详细需求数据。", styles["BodyCN"]))
        
        elements.append(Spacer(1, 12))
        
        # ---- 反馈记录 ----
        feedbacks = order_dict.get("feedbacks", [])
        if feedbacks:
            elements.append(Paragraph("三、客户反馈记录", styles["SectionTitle"]))
            
            fb_header = [["时间", "类型", "内容"]]
            fb_rows = []
            for fb in feedbacks:
                fb_type = "确认通过" if fb.get("type") == "approval" else "需要修改"
                fb_time = _format_time(fb.get("createdAt", ""))
                fb_content = (fb.get("content", "") or "-")[:80]
                fb_rows.append([fb_time, fb_type, fb_content])
            
            fb_table = Table(fb_header + fb_rows, colWidths=[120, 70, 270])
            fb_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), _FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0071e3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(fb_table)
            elements.append(Spacer(1, 12))
        
        # ---- 预览历史 ----
        preview_history = order_data.get("previewHistory", [])
        if preview_history:
            section_num = "四" if feedbacks else "三"
            elements.append(Paragraph(f"{section_num}、预览提交记录", styles["SectionTitle"]))
            
            ph_header = [["时间", "类型", "审核状态", "操作者"]]
            ph_rows = []
            for ph in preview_history:
                ph_time = _format_time(ph.get("createdAt", ""))
                ph_type = "终稿" if ph.get("previewType") == "final" else "初稿"
                review_map = {"pending": "待审核", "approved": "已通过", "rejected": "已拒绝"}
                ph_status = review_map.get(ph.get("reviewStatus", ""), ph.get("reviewStatus", ""))
                ph_by = ph.get("createdByName", "-")
                ph_rows.append([ph_time, ph_type, ph_status, ph_by])
            
            ph_table = Table(ph_header + ph_rows, colWidths=[120, 60, 90, 190])
            ph_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), _FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0071e3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(ph_table)
        
        elements.append(Spacer(1, 24))
        
        # ---- 页脚 ----
        elements.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#d0d0d0"), spaceAfter=6))
        now_beijing = beijing_now()
        elements.append(Paragraph(
            f"Unique Vision AI · 内部订单详情 · 导出时间：{now_beijing.strftime('%Y-%m-%d %H:%M')} · 仅供内部使用",
            styles["Footer"]
        ))
        
        doc.build(
            elements,
            onFirstPage=_draw_confirmation_watermark,
            onLaterPages=_draw_confirmation_watermark,
        )
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
