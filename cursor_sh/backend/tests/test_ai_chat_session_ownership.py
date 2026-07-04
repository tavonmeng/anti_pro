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


class _FakeUser:
    id = "user-a"
    username = "Alice"


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


@pytest.mark.asyncio
async def test_chat_history_state_loads_owned_agent_state(monkeypatch):
    existing = AIChatSession(
        id="session-1",
        user_id="user-a",
        username="Alice",
        business_type="ai_3d_custom",
    )
    fake_db = _FakeDb(existing)
    captured = {}

    def _fake_load_agent_state(session_id, user_id, business_type):
        captured.update(
            {
                "session_id": session_id,
                "user_id": user_id,
                "business_type": business_type,
            }
        )
        return {
            "current_agent": "brief_agent",
            "stage": "brief_building",
            "brief_state": {"fields": {"theme_concept": {"value": "毛绒大熊猫"}}},
        }

    monkeypatch.setattr(ai_chat_history, "load_agent_state", _fake_load_agent_state)

    response = await ai_chat_history.get_session_state(
        "session-1",
        _FakeUser(),
        fake_db,
    )

    assert response["code"] == 200
    assert response["data"]["brief_state"]["fields"]["theme_concept"]["value"] == "毛绒大熊猫"
    assert captured == {
        "session_id": "session-1",
        "user_id": "user-a",
        "business_type": "ai_3d_custom",
    }
