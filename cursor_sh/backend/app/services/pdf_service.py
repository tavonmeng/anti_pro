"""PDF 生成服务 - 需求告知函 / 订单确认函"""

import io
import os
import platform
from datetime import datetime, timezone, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


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
            print(f"  📝 PDF 字体: {path}")
            return "ttf"
    
    # 第二层：通过 fc-list 动态查找（仅 Linux）
    if system == "Linux":
        fc_path = _find_linux_cjk_font_via_fc()
        if fc_path:
            if _try_register_ttfont(fc_path, "Chinese"):
                _try_register_ttfont(fc_path, "ChineseBold")
                print(f"  📝 PDF 字体 (fc-list): {fc_path}")
                return "ttf"
    
    # 第三层：使用 ReportLab 内置 CID 字体（不需要任何外部文件）
    try:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        print("  📝 PDF 字体: STSong-Light (CID 内置)")
        return "cid"
    except Exception:
        pass
    
    # 全部失败
    print("  ⚠️  未找到中文字体，PDF 将无法正确显示中文")
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
    "video_purchase": "裸眼3D成片购买适配",
    "ai_3d_custom": "AI裸眼3D内容定制",
    "digital_art": "数字艺术内容定制",
}

STATUS_MAP = {
    "draft": "草稿",
    "pending_assign": "待分配",
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
        beijing = dt.astimezone(timezone(timedelta(hours=8)))
        return beijing.strftime("%Y年%m月%d日 %H:%M")
    except Exception:
        return time_str


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
                rows.append((label, str(val)))
        
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


# ========== 核心 PDF 生成方法 ==========

class PDFService:
    """PDF 生成服务"""

    @staticmethod
    def generate_order_confirmation_pdf(order_dict: dict) -> bytes:
        """
        生成需求告知函 PDF。
        
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
        order_type_text = ORDER_TYPE_MAP.get(order_type, order_type)
        order_data = order_dict.get("orderData", {})
        status = order_dict.get("status", "")
        status_text = STATUS_MAP.get(status, status)
        user_name = order_dict.get("userName", "-")
        created_at = _format_time(order_dict.get("createdAt", ""))
        
        # ---- 标题 ----
        elements.append(Paragraph("需 求 告 知 函", styles["DocTitle"]))
        elements.append(Paragraph(f"编号：{order_number}", styles["DocSubtitle"]))
        elements.append(HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.HexColor("#e0e0e0"),
            spaceAfter=12,
        ))
        
        # ---- 致辞 ----
        elements.append(Paragraph("尊敬的客户：", styles["BodyCN"]))
        elements.append(Spacer(1, 4))
        greeting = (
            f"&nbsp;&nbsp;&nbsp;&nbsp;感谢您选择 <b>Unique Video AI 设计平台</b>。"
            f"以下是您提交的需求确认摘要，经您签名确认后即视为需求确认完成，我们将立即进入制作流程。"
        )
        elements.append(Paragraph(greeting, styles["BodyCN"]))
        elements.append(Spacer(1, 8))
        
        # ---- 一、基本信息 ----
        elements.append(Paragraph("一、基本信息", styles["SectionTitle"]))
        
        basic_data = [
            ["订单编号", order_number],
            ["订单类型", order_type_text],
            ["订单状态", status_text],
            ["提交用户", user_name],
            ["创建时间", created_at],
        ]
        
        # 负责人
        assignees = order_dict.get("assignees", [])
        if assignees:
            names = ", ".join([a.get("name", "") for a in assignees])
            basic_data.append(["负责人", names])
        
        basic_table = Table(basic_data, colWidths=[120, 340])
        basic_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), _FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#86868b")),
            ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1a1c1c")),
            ("FONTNAME", (1, 0), (1, -1), _FONT_BOLD),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fafafa")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e8e8e8")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(basic_table)
        elements.append(Spacer(1, 12))
        
        # ---- 二、需求摘要 ----
        elements.append(Paragraph("二、需求摘要", styles["SectionTitle"]))
        
        summary_rows = _build_summary_rows(order_data, order_type)
        
        if summary_rows:
            summary_table = Table(summary_rows, colWidths=[120, 340])
            summary_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), _FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#86868b")),
                ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1a1c1c")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fafafa")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e8e8e8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]))
            elements.append(summary_table)
        else:
            elements.append(Paragraph("暂无详细需求数据。", styles["BodyCN"]))
        
        elements.append(Spacer(1, 12))
        
        # ---- 三、制作排期 ----
        elements.append(Paragraph("三、制作排期", styles["SectionTitle"]))
        
        prod_days_map = {"video_purchase": 5, "ai_3d_custom": 15, "digital_art": 7}
        prod_days = prod_days_map.get(order_type, 15)
        
        elements.append(Paragraph(
            f"预计制作周期：<b>{prod_days} 个工作日</b>",
            styles["BodyCN"]
        ))
        elements.append(Spacer(1, 8))
        
        # ---- 四、确认声明 ----
        elements.append(HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.HexColor("#e0e0e0"),
            spaceBefore=8,
            spaceAfter=12,
        ))
        
        elements.append(Paragraph("四、确认声明", styles["SectionTitle"]))
        declaration = (
            "&nbsp;&nbsp;&nbsp;&nbsp;本人已仔细阅读并确认以上需求内容及制作排期安排，"
            "同意按照上述内容进入制作流程。确认后，需求内容不可修改。"
        )
        elements.append(Paragraph(declaration, styles["BodyCN"]))
        elements.append(Spacer(1, 20))
        
        # 签名区域
        confirm_info = order_data.get("confirmEmail", "") or order_data.get("confirmPhone", "")
        sign_data = [
            ["确认人", user_name, "确认方式", "线上签名确认"],
            ["联系方式", confirm_info or "-", "确认时间", created_at],
        ]
        sign_table = Table(sign_data, colWidths=[80, 150, 80, 150])
        sign_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), _FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#86868b")),
            ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#86868b")),
            ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1a1c1c")),
            ("TEXTCOLOR", (3, 0), (3, -1), colors.HexColor("#1a1c1c")),
            ("FONTNAME", (1, 0), (1, -1), _FONT_BOLD),
            ("FONTNAME", (3, 0), (3, -1), _FONT_BOLD),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e8e8e8")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(sign_table)
        
        elements.append(Spacer(1, 30))
        
        # ---- 页脚 ----
        elements.append(HRFlowable(
            width="100%",
            thickness=0.3,
            color=colors.HexColor("#d0d0d0"),
            spaceAfter=8,
        ))
        
        now_beijing = datetime.now(timezone(timedelta(hours=8)))
        elements.append(Paragraph(
            f"Unique Video AI 设计平台 · 本文件由系统自动生成 · {now_beijing.strftime('%Y-%m-%d %H:%M')}",
            styles["Footer"]
        ))
        
        # 构建 PDF
        doc.build(elements)
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
            summary_table = Table(summary_rows, colWidths=[120, 340])
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
        now_beijing = datetime.now(timezone(timedelta(hours=8)))
        elements.append(Paragraph(
            f"Unique Video AI · 内部订单详情 · 导出时间：{now_beijing.strftime('%Y-%m-%d %H:%M')} · 仅供内部使用",
            styles["Footer"]
        ))
        
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
