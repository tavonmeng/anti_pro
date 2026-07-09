from app.middleware.audit_logger import should_skip_audit_logging


def test_website_visit_tracking_skips_audit_logging():
    assert should_skip_audit_logging("/api/website-analytics/visit") is True
    assert should_skip_audit_logging("/api/orders") is False
