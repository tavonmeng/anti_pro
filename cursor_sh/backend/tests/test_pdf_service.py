import pytest
from reportlab.platypus import Paragraph
from reportlab.platypus import SimpleDocTemplate
from reportlab.platypus import Table as ReportLabTable

from app.services import pdf_service
from app.services.pdf_service import PDFService


def test_order_detail_requirement_cells_wrap_long_text(monkeypatch):
    captured_summary_tables = []

    def recording_table(data, *args, **kwargs):
        if kwargs.get("colWidths") == [120, 340]:
            captured_summary_tables.append(data)
        return ReportLabTable(data, *args, **kwargs)

    monkeypatch.setattr("app.services.pdf_service.Table", recording_table)

    long_requirement = (
        "这是一个很长的内容需求，需要在订单详情报告 PDF 的需求明细表格中按列宽自动换行，"
        "否则管理员下载后会看到文字横向溢出页面。"
    )

    PDFService.generate_order_detail_pdf(
        {
            "orderNumber": "UV-TEST-001",
            "orderType": "ai_3d_custom",
            "status": "pending_assign",
            "userName": "测试客户",
            "createdAt": "2026-07-08T10:00:00+08:00",
            "updatedAt": "2026-07-08T10:00:00+08:00",
            "revisionCount": 0,
            "feedbacks": [],
            "orderData": {
                "brand": "测试品牌",
                "content": long_requirement,
            },
        }
    )

    assert captured_summary_tables
    content_row = next(row for row in captured_summary_tables[-1] if row[0].getPlainText() == "内容需求")
    assert isinstance(content_row[1], Paragraph)
    assert content_row[1].getPlainText() == long_requirement[:100]


def test_order_detail_pdf_uses_logo_watermark_background(monkeypatch):
    captured_build_kwargs = {}
    original_build = SimpleDocTemplate.build

    def recording_build(self, flowables, *args, **kwargs):
        captured_build_kwargs.update(kwargs)
        return original_build(self, flowables, *args, **kwargs)

    monkeypatch.setattr("app.services.pdf_service.SimpleDocTemplate.build", recording_build)

    PDFService.generate_order_detail_pdf(
        {
            "orderNumber": "UV-TEST-LOGO",
            "orderType": "ai_3d_custom",
            "status": "pending_assign",
            "userName": "测试客户",
            "createdAt": "2026-07-08T10:00:00+08:00",
            "updatedAt": "2026-07-08T10:00:00+08:00",
            "revisionCount": 0,
            "feedbacks": [],
            "orderData": {
                "brand": "测试品牌",
                "content": "测试需求",
            },
        }
    )

    assert captured_build_kwargs["onFirstPage"] is pdf_service._draw_confirmation_watermark
    assert captured_build_kwargs["onLaterPages"] is pdf_service._draw_confirmation_watermark


def test_watermark_draws_complementary_logo_halves():
    class FakeCanvas:
        def __init__(self):
            self.draws = []
            self.translates = []

        def setFillAlpha(self, value):
            pass

        def setStrokeAlpha(self, value):
            pass

        def saveState(self):
            pass

        def restoreState(self):
            pass

        def translate(self, x, y):
            self.translates.append((x, y))

        def scale(self, x, y):
            pass

        def drawImage(self, logo_path, x, y, width, height, mask=None):
            self.draws.append((x, y, width, height))

    canvas = FakeCanvas()

    pdf_service._draw_confirmation_watermark(canvas, None)

    page_width, page_height = pdf_service.A4
    watermark_height = 340 * pdf_service.mm
    watermark_width = watermark_height * (466 / 831)
    visible_width = watermark_width / 2
    expected_left_image_x = -(watermark_width - visible_width)
    expected_right_image_x = page_width - visible_width
    expected_y = (page_height - watermark_height) / 2

    assert canvas.translates[0] == pytest.approx((expected_left_image_x, expected_y + watermark_height))
    assert canvas.draws[1][0] == pytest.approx(expected_right_image_x)
    assert visible_width * 2 == pytest.approx(watermark_width)
