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
async def alex(client):
    client.headers["Authorization"] = "Bearer test-alex-token"
    return client

@pytest.fixture
async def jason(client):
    client.headers["Authorization"] = "Bearer test-jason-token"
    return client


async def test_verify_valid_token(client):
    r = await client.post("/auth/verify", headers={"Authorization": "Bearer test-alex-token"})
    assert r.status_code == 200
    assert r.json()["username"] == "alex"

async def test_verify_jason_token(client):
    r = await client.post("/auth/verify", headers={"Authorization": "Bearer test-jason-token"})
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
