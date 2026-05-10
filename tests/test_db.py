import pytest
import db
import aiosqlite

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
async def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    await db.init_db()


async def test_create_and_list_sessions():
    s = await db.create_session("alex", "llama3.1:8b")
    assert s["model"] == "llama3.1:8b"
    assert "id" in s

    sessions = await db.list_sessions("alex")
    assert len(sessions) == 1
    assert sessions[0]["id"] == s["id"]
    assert sessions[0]["title"] is None


async def test_sessions_scoped_by_username():
    await db.create_session("alex", "llama3.1:8b")
    assert await db.list_sessions("jason") == []


async def test_delete_session():
    s = await db.create_session("alex", "gemma4:e4b")
    deleted = await db.delete_session(s["id"], "alex")
    assert deleted is True
    assert await db.list_sessions("alex") == []


async def test_delete_wrong_user_returns_false():
    s = await db.create_session("alex", "llama3.1:8b")
    deleted = await db.delete_session(s["id"], "jason")
    assert deleted is False


async def test_add_and_get_messages():
    s = await db.create_session("alex", "llama3.1:8b")
    await db.add_message(s["id"], "user", "hello")
    await db.add_message(s["id"], "assistant", "...")

    msgs = await db.get_messages(s["id"])
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["content"] == "..."


async def test_message_count():
    s = await db.create_session("alex", "llama3.1:8b")
    assert await db.message_count(s["id"]) == 0
    await db.add_message(s["id"], "user", "hi")
    assert await db.message_count(s["id"]) == 1


async def test_set_and_get_session_title():
    s = await db.create_session("alex", "llama3.1:8b")
    await db.set_session_title(s["id"], "alex", "My Test Chat")
    sessions = await db.list_sessions("alex")
    assert sessions[0]["title"] == "My Test Chat"


async def test_get_session_returns_correct_row():
    s = await db.create_session("alex", "gemma4:e4b")
    row = await db.get_session(s["id"], "alex")
    assert row is not None
    assert row["id"] == s["id"]
    assert row["model"] == "gemma4:e4b"


async def test_get_session_wrong_user_returns_none():
    s = await db.create_session("alex", "llama3.1:8b")
    assert await db.get_session(s["id"], "jason") is None


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
    s = await db.create_session("alex", "llama3.1:8b")
    sessions_before = await db.list_sessions("alex")
    ts_before = sessions_before[0]["updated_at"]

    await db.add_message(s["id"], "user", "hi")
    sessions_after = await db.list_sessions("alex")
    assert sessions_after[0]["updated_at"] >= ts_before


async def test_migrates_legacy_mode_column(tmp_path, monkeypatch):
    legacy_path = str(tmp_path / "legacy.db")
    monkeypatch.setattr(db, "DB_PATH", legacy_path)

    async with aiosqlite.connect(legacy_path) as conn:
        await conn.executescript("""
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                title TEXT,
                mode TEXT NOT NULL CHECK(mode IN ('moc', 'serious')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            INSERT INTO sessions VALUES ('s1', 'alex', 'old chat', 'moc', '2026-01-01', '2026-01-01');
            INSERT INTO sessions VALUES ('s2', 'alex', 'serious one', 'serious', '2026-01-01', '2026-01-01');
        """)
        await conn.commit()

    await db.init_db()

    rows = await db.list_sessions("alex")
    by_id = {r["id"]: r for r in rows}
    assert by_id["s1"]["model"] == "llama3.1:8b"
    assert by_id["s2"]["model"] == "gemma4:e4b"
