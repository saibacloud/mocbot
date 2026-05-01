import aiosqlite
import os
import uuid
from datetime import datetime, timezone

DB_PATH = os.getenv("MOCHA_DB", "mocha.db")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                title TEXT,
                mode TEXT NOT NULL CHECK(mode IN ('moc', 'serious')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_contexts (
                username TEXT PRIMARY KEY,
                context TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
        """)
        await db.commit()


async def create_session(username: str, mode: str) -> dict:
    sid = str(uuid.uuid4())
    ts = _now()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sessions (id, username, title, mode, created_at, updated_at) "
            "VALUES (?, ?, NULL, ?, ?, ?)",
            (sid, username, mode, ts, ts),
        )
        await db.commit()
    return {"id": sid, "mode": mode, "created_at": ts}


async def list_sessions(username: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, title, mode, created_at, updated_at FROM sessions "
            "WHERE username = ? ORDER BY updated_at DESC",
            (username,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_session(session_id: str, username: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, username, title, mode, created_at, updated_at FROM sessions "
            "WHERE id = ? AND username = ?",
            (session_id, username),
        ) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None


async def delete_session(session_id: str, username: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM sessions WHERE id = ? AND username = ?",
            (session_id, username),
        )
        await db.commit()
        rowcount = cursor.rowcount
    return rowcount > 0


async def add_message(session_id: str, role: str, content: str):
    ts = _now()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (id, session_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), session_id, role, content, ts),
        )
        await db.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (ts, session_id),
        )
        await db.commit()


async def get_messages(session_id: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def message_count(session_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?",
            (session_id,),
        ) as cursor:
            row = await cursor.fetchone()
    return row[0]


async def set_session_title(session_id: str, username: str, title: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET title = ? WHERE id = ? AND username = ?",
            (title, session_id, username),
        )
        await db.commit()


async def get_context(username: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT context FROM user_contexts WHERE username = ?",
            (username,),
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else ""


async def set_context(username: str, context: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO user_contexts (username, context, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(username) DO UPDATE SET context = excluded.context, updated_at = excluded.updated_at",
            (username, context, _now()),
        )
        await db.commit()
