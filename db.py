import aiosqlite
import os
import uuid
from datetime import datetime, timezone

DB_PATH = os.getenv("MOCHA_DB", "mocha.db")

_MODE_TO_MODEL = {"moc": "llama3.1:8b", "serious": "gemma4:e4b"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _migrate_mode_to_model(db):
    async with db.execute("PRAGMA table_info(sessions)") as cur:
        cols = [row[1] for row in await cur.fetchall()]

    if "mode" not in cols or "model" in cols:
        return

    await db.execute("PRAGMA foreign_keys=OFF")
    await db.executescript("""
        CREATE TABLE sessions_new (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            title TEXT,
            model TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        INSERT INTO sessions_new (id, username, title, model, created_at, updated_at)
        SELECT id, username, title,
               CASE mode
                   WHEN 'moc' THEN 'llama3.1:8b'
                   WHEN 'serious' THEN 'gemma4:e4b'
                   ELSE mode
               END,
               created_at, updated_at
        FROM sessions;
        DROP TABLE sessions;
        ALTER TABLE sessions_new RENAME TO sessions;
    """)
    await db.commit()
    await db.execute("PRAGMA foreign_keys=ON")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")

        await _migrate_mode_to_model(db)

        await db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                title TEXT,
                model TEXT NOT NULL,
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


async def create_session(username: str, model: str) -> dict:
    sid = str(uuid.uuid4())
    ts = _now()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sessions (id, username, title, model, created_at, updated_at) "
            "VALUES (?, ?, NULL, ?, ?, ?)",
            (sid, username, model, ts, ts),
        )
        await db.commit()
    return {"id": sid, "model": model, "created_at": ts}


async def list_sessions(username: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, title, model, created_at, updated_at FROM sessions "
            "WHERE username = ? ORDER BY updated_at DESC",
            (username,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_session(session_id: str, username: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, username, title, model, created_at, updated_at FROM sessions "
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
