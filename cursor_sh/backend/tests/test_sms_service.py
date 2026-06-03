from app.services.sms_service import _is_frequency_limited_error


def test_aliyun_check_frequency_error_is_rate_limited():
    assert _is_frequency_limited_error("isv.BUSINESS_LIMIT_CONTROL", "check frequency failed")


def test_chinese_frequency_error_is_rate_limited():
    assert _is_frequency_limited_error("验证码发送频繁，请稍后重试")


def test_regular_provider_error_is_not_rate_limited():
    assert not _is_frequency_limited_error("InvalidAccessKeyId", "specified access key is not found")
