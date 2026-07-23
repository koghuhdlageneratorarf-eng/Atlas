"""
atlas_core/session.py — SQLite память сессии Atlas Code Agent
Сохраняет историю сообщений между перезапусками.
"""

import sqlite3
import json
import datetime
from pathlib import Path
from typing import List, Dict, Optional

DB_PATH = Path(__file__).parent.parent / "Memory" / "atlas_sessions.db"


def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,  -- 'system', 'user', 'assistant', 'tool'
            content TEXT NOT NULL,
            tool_calls TEXT,      -- JSON список tool_calls
            tool_call_id TEXT,    -- ID для tool response
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    conn.commit()
    conn.close()


class SessionManager:
    """Управление сессиями: создание, загрузка, сохранение сообщений."""

    def __init__(self, session_name: str = "default"):
        _init_db()
        self.session_name = session_name
        self.session_id = self._get_or_create_session()

    def _get_or_create_session(self) -> int:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(
            "SELECT id FROM sessions WHERE session_name = ?",
            (self.session_name,)
        )
        row = cursor.fetchone()
        if row:
            sid = row[0]
        else:
            cursor = conn.execute(
                "INSERT INTO sessions (session_name) VALUES (?)",
                (self.session_name,)
            )
            sid = cursor.lastrowid
            conn.commit()
        conn.close()
        return sid

    def add_message(
        self,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
        tool_call_id: Optional[str] = None
    ):
        """Добавить сообщение в сессию."""
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """INSERT INTO messages (session_id, role, content, tool_calls, tool_call_id)
               VALUES (?, ?, ?, ?, ?)""",
            (
                self.session_id,
                role,
                content,
                json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
                tool_call_id
            )
        )
        conn.execute(
            "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (self.session_id,)
        )
        conn.commit()
        conn.close()

    def get_history(self, limit: int = 50) -> List[Dict]:
        """Получить последние N сообщений сессии."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(
            """SELECT role, content, tool_calls, tool_call_id
               FROM messages
               WHERE session_id = ?
               ORDER BY timestamp ASC
               LIMIT ?""",
            (self.session_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()

        history = []
        for role, content, tool_calls_raw, tool_call_id in rows:
            msg = {"role": role, "content": content}
            if tool_calls_raw:
                msg["tool_calls"] = json.loads(tool_calls_raw)
            if tool_call_id:
                msg["tool_call_id"] = tool_call_id
            history.append(msg)
        return history

    def clear_history(self):
        """Очистить сообщения текущей сессии (сохранить сессию)."""
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM messages WHERE session_id = ?", (self.session_id,))
        conn.commit()
        conn.close()

    def list_sessions(self) -> List[Dict]:
        """Список всех сессий."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(
            "SELECT id, session_name, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
        )
        sessions = [
            {"id": row[0], "name": row[1], "created": row[2], "updated": row[3]}
            for row in cursor.fetchall()
        ]
        conn.close()
        return sessions

    def delete_session(self, session_name: str):
        """Удалить сессию и все её сообщения."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(
            "SELECT id FROM sessions WHERE session_name = ?", (session_name,)
        )
        row = cursor.fetchone()
        if row:
            sid = row[0]
            conn.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))
            conn.commit()
        conn.close()


# --- CLI тест ---
if __name__ == "__main__":
    sm = SessionManager("test")
    sm.clear_history()
    sm.add_message("system", "Ты — Atlas Code Agent.")
    sm.add_message("user", "Привет!")
    sm.add_message("assistant", "Привет! Чем могу помочь?")

    hist = sm.get_history()
    for m in hist:
        print(f"[{m['role']}] {m['content'][:60]}...")

    print(f"\\nВсего сессий: {len(sm.list_sessions())}")
