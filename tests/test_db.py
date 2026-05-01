import pytest
import db

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
async def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    await db.init_db()


async def test_create_and_list_sessions():
    s = await db.create_session("alex", "moc")
    assert s["mode"] == "moc"
    assert "id" in s

    sessions = await db.list_sessions("alex")
    assert len(sessions) == 1
    assert sessions[0]["id"] == s["id"]
    assert sessions[0]["title"] is None


async def test_sessions_scoped_by_username():
    await db.create_session("alex", "moc")
    assert await db.list_sessions("jason") == []


async def test_delete_session():
    s = await db.create_session("alex", "serious")
    deleted = await db.delete_session(s["id"], "alex")
    assert deleted is True
    assert await db.list_sessions("alex") == []


async def test_delete_wrong_user_returns_false():
    s = await db.create_session("alex", "moc")
    deleted = await db.delete_session(s["id"], "jason")
    assert deleted is False


async def test_add_and_get_messages():
    s = await db.create_session("alex", "moc")
    await db.add_message(s["id"], "user", "hello")
    await db.add_message(s["id"], "assistant", "...")

    msgs = await db.get_messages(s["id"])
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["content"] == "..."


async def test_message_count():
    s = await db.create_session("alex", "moc")
    assert await db.message_count(s["id"]) == 0
    await db.add_message(s["id"], "user", "hi")
    assert await db.message_count(s["id"]) == 1


async def test_set_and_get_session_title():
    s = await db.create_session("alex", "moc")
    await db.set_session_title(s["id"], "My Test Chat")
    sessions = await db.list_sessions("alex")
    assert sessions[0]["title"] == "My Test Chat"


async def test_get_context_default_empty():
    assert await db.get_context("alex") == ""


async def test_set_and_get_context():
    await db.set_context("alex", "I am a security engineer.")
    assert await db.get_context("alex") == "I am a security engineer."


async def test_set_context_upserts():
    await db.set_context("alex", "first")
    await db.set_context("alex", "second")
    assert await db.get_context("alex") == "second"


async def test_updated_at_bumped_on_message():
    s = await db.create_session("alex", "moc")
    sessions_before = await db.list_sessions("alex")
    ts_before = sessions_before[0]["updated_at"]

    await db.add_message(s["id"], "user", "hi")
    sessions_after = await db.list_sessions("alex")
    assert sessions_after[0]["updated_at"] >= ts_before
