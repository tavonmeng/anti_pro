import pytest
from fastapi import HTTPException

from app import database as database_module
from app.api import ai as ai_module
from app.api import ai_chat_history
from app.models.ai_chat import AIChatSession


def test_existing_ai_chat_session_rejects_different_user():
    session = AIChatSession(id="session-1", user_id="user-a", username="A")

    with pytest.raises(HTTPException) as exc:
        ai_chat_history._ensure_session_owner(session, "user-b", "B")

    assert exc.value.status_code == 403
    assert session.user_id == "user-a"


def test_anonymous_ai_chat_session_can_be_claimed_by_logged_in_user():
    session = AIChatSession(id="session-1", user_id="anonymous", username="anonymous")

    ai_chat_history._ensure_session_owner(session, "user-a", "Alice")

    assert session.user_id == "user-a"
    assert session.username == "Alice"


class _FakeResult:
    def __init__(self, session):
        self._session = session

    def scalar_one_or_none(self):
        return self._session


class _FakeDb:
    def __init__(self, session):
        self.session = session
        self.added = []
        self.committed = False
        self.execute_count = 0

    async def execute(self, _statement):
        self.execute_count += 1
        return _FakeResult(self.session)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass


class _FakeSessionContext:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, *_):
        return False


@pytest.mark.asyncio
async def test_ai_background_save_skips_cross_user_session(monkeypatch):
    existing = AIChatSession(id="session-1", user_id="user-a", username="A")
    fake_db = _FakeDb(existing)

    monkeypatch.setattr(database_module, "async_session_maker", lambda: _FakeSessionContext(fake_db))
    monkeypatch.setattr(ai_module, "log_business_event", lambda *_, **__: None)

    await ai_module._save_to_db(
        session_id="session-1",
        user_id="user-b",
        username="B",
        user_msg="hello",
        assistant_msg="hi",
    )

    assert fake_db.execute_count == 1
    assert fake_db.added == []
    assert fake_db.committed is False
    assert existing.user_id == "user-a"
