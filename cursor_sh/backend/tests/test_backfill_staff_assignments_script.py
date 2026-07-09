from scripts.backfill_staff_assignments import _is_missing_table_error


def test_is_missing_table_error_detects_sqlite_missing_table_message():
    error = RuntimeError("sqlite3.OperationalError: no such table: order_assignees")

    assert _is_missing_table_error(error) is True


def test_is_missing_table_error_ignores_other_errors():
    error = RuntimeError("connection refused")

    assert _is_missing_table_error(error) is False
