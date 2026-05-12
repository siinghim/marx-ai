from __future__ import annotations
import aiosqlite
import json
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/sessions.db")


async def get_db() -> aiosqlite.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '新对话',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            sources_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        )
    """)
    await db.execute("PRAGMA foreign_keys = ON")
    await db.commit()
    return db


async def create_session(title: str = "新对话") -> dict:
    db = await get_db()
    sid = uuid.uuid4().hex[:12]
    now = datetime.now().isoformat()
    await db.execute(
        "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (sid, title, now, now),
    )
    await db.commit()
    await db.close()
    return {"id": sid, "title": title, "created_at": now, "updated_at": now}


async def list_sessions() -> list[dict]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM sessions ORDER BY updated_at DESC")
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def delete_session(session_id: str) -> bool:
    db = await get_db()
    cursor = await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    await db.commit()
    deleted = cursor.rowcount > 0
    await db.close()
    return deleted


async def get_messages(session_id: str, limit: int = 40) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
        (session_id, limit),
    )
    rows = await cursor.fetchall()
    await db.close()
    return [
        {
            "id": r["id"],
            "session_id": r["session_id"],
            "role": r["role"],
            "content": r["content"],
            "sources": json.loads(r["sources_json"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


async def add_message(session_id: str, role: str, content: str, sources: list[dict] | None = None) -> dict:
    db = await get_db()
    now = datetime.now().isoformat()
    sources_json = json.dumps(sources or [], ensure_ascii=False)
    cursor = await db.execute(
        "INSERT INTO messages (session_id, role, content, sources_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, sources_json, now),
    )
    await db.execute(
        "UPDATE sessions SET updated_at = ? WHERE id = ?",
        (now, session_id),
    )
    await db.commit()
    msg_id = cursor.lastrowid
    await db.close()
    return {"id": msg_id, "session_id": session_id, "role": role, "content": content, "sources": sources or [], "created_at": now}


async def update_session_title(session_id: str, title: str) -> None:
    db = await get_db()
    await db.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (title, datetime.now().isoformat(), session_id))
    await db.commit()
    await db.close()
