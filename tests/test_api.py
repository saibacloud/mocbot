import json
import pytest
import db
from httpx import AsyncClient, ASGITransport
from app import app

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
async def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    await db.init_db()

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.fixture
async def alex():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           headers={"Authorization": "Bearer test-alex-token"}) as c:
        yield c

@pytest.fixture
async def jason():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           headers={"Authorization": "Bearer test-jason-token"}) as c:
        yield c


async def test_verify_valid_token(client):
    r = await client.post("/auth/verify", headers={"Authorization": "Bearer test-alex-token"})
    assert r.status_code == 200
    assert r.json()["username"] == "alex"

async def test_verify_jason_token(client):
    r = await client.post("/auth/verify", headers={"Authorization": "Bearer test-jason-token"})
    assert r.status_code == 200
    assert r.json()["username"] == "jason"

async def test_verify_invalid_token(client):
    r = await client.post("/auth/verify", headers={"Authorization": "Bearer bad"})
    assert r.status_code == 401

async def test_verify_no_token(client):
    r = await client.post("/auth/verify")
    assert r.status_code == 401

async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert "status" in r.json()

async def test_create_session_moc(alex):
    r = await alex.post("/sessions", json={"mode": "moc"})
    assert r.status_code == 201
    data = r.json()
    assert data["mode"] == "moc"
    assert "id" in data

async def test_create_session_serious(alex):
    r = await alex.post("/sessions", json={"mode": "serious"})
    assert r.status_code == 201
    assert r.json()["mode"] == "serious"

async def test_create_session_invalid_mode(alex):
    r = await alex.post("/sessions", json={"mode": "banana"})
    assert r.status_code == 400

async def test_list_sessions_empty(alex):
    r = await alex.get("/sessions")
    assert r.status_code == 200
    assert r.json() == []

async def test_list_sessions_returns_user_sessions_only(alex, jason):
    await alex.post("/sessions", json={"mode": "moc"})
    r = await jason.get("/sessions")
    assert r.json() == []

async def test_delete_session(alex):
    sid = (await alex.post("/sessions", json={"mode": "moc"})).json()["id"]
    r = await alex.delete(f"/sessions/{sid}")
    assert r.status_code == 204
    assert (await alex.get("/sessions")).json() == []

async def test_delete_session_wrong_user(alex, jason):
    sid = (await alex.post("/sessions", json={"mode": "moc"})).json()["id"]
    r = await jason.delete(f"/sessions/{sid}")
    assert r.status_code == 404

async def test_get_messages_empty(alex):
    sid = (await alex.post("/sessions", json={"mode": "moc"})).json()["id"]
    r = await alex.get(f"/sessions/{sid}/messages")
    assert r.status_code == 200
    assert r.json() == []

async def test_get_messages_wrong_user(alex, jason):
    sid = (await alex.post("/sessions", json={"mode": "moc"})).json()["id"]
    r = await jason.get(f"/sessions/{sid}/messages")
    assert r.status_code == 404

async def test_context_default_empty(alex):
    r = await alex.get("/context")
    assert r.status_code == 200
    assert r.json()["context"] == ""

async def test_context_save_and_load(alex):
    await alex.put("/context", json={"context": "I focus on threat modelling."})
    r = await alex.get("/context")
    assert r.json()["context"] == "I focus on threat modelling."

async def test_context_scoped_to_user(alex, jason):
    await alex.put("/context", json={"context": "alex context"})
    r = await jason.get("/context")
    assert r.json()["context"] == ""


from unittest.mock import AsyncMock, patch

def make_ollama_stream(chunks: list[str]):
    """Build a mock async iterator that yields SSE-like Ollama response lines."""
    lines = [json.dumps({"message": {"content": c}}) for c in chunks]
    lines.append(json.dumps({"done": True}))

    async def aiter_lines():
        for line in lines:
            yield line

    mock_response = AsyncMock()
    mock_response.aiter_lines = aiter_lines
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    return mock_response


def make_ollama_title_response(title: str):
    return AsyncMock(
        json=AsyncMock(return_value={"message": {"content": title}})
    )


async def test_chat_streams_response(alex):
    sid = (await alex.post("/sessions", json={"mode": "moc"})).json()["id"]

    stream_mock = make_ollama_stream(["hello", " there"])
    title_mock = make_ollama_title_response("Hello There Chat")

    with patch("httpx.AsyncClient") as mock_client_cls:
        instance = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        instance.stream.return_value = stream_mock
        instance.post = AsyncMock(return_value=title_mock)

        r = await alex.post(f"/sessions/{sid}/chat", json={"message": "hi"})

    assert r.status_code == 200
    body = r.text
    assert "hello" in body
    assert '"done": true' in body


async def test_chat_saves_messages(alex):
    sid = (await alex.post("/sessions", json={"mode": "moc"})).json()["id"]

    stream_mock = make_ollama_stream(["meow"])
    title_mock = make_ollama_title_response("Meow Chat")

    with patch("httpx.AsyncClient") as mock_client_cls:
        instance = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        instance.stream.return_value = stream_mock
        instance.post = AsyncMock(return_value=title_mock)

        await alex.post(f"/sessions/{sid}/chat", json={"message": "hello mocha"})

    msgs = (await alex.get(f"/sessions/{sid}/messages")).json()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "hello mocha"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == "meow"


async def test_chat_wrong_session_returns_404(alex, jason):
    sid = (await alex.post("/sessions", json={"mode": "moc"})).json()["id"]
    r = await jason.post(f"/sessions/{sid}/chat", json={"message": "hi"})
    assert r.status_code == 404


async def test_chat_empty_message_returns_400(alex):
    sid = (await alex.post("/sessions", json={"mode": "moc"})).json()["id"]
    r = await alex.post(f"/sessions/{sid}/chat", json={"message": "   "})
    assert r.status_code == 400
