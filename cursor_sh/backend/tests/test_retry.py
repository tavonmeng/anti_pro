from app.utils.log_setup import get_module_logger
from app.utils.retry import RetryableExternalError, retry_sync


def test_retry_sync_retries_retryable_error():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RetryableExternalError("temporary")
        return "ok"

    result = retry_sync(
        flaky,
        logger=get_module_logger("system"),
        event="test_external_call",
        attempts=3,
        fields={"case": "retry"},
    )

    assert result == "ok"
    assert attempts["count"] == 3


def test_retry_sync_stops_on_non_retryable_error():
    attempts = {"count": 0}

    def fail():
        attempts["count"] += 1
        raise ValueError("bad input")

    try:
        retry_sync(
            fail,
            logger=get_module_logger("system"),
            event="test_external_call",
            attempts=3,
            fields={"case": "non_retryable"},
            should_retry=lambda exc: isinstance(exc, RetryableExternalError),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("retry_sync should re-raise non-retryable errors")

    assert attempts["count"] == 1
