"""SQLite persistent memory for JARVIS."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from jarvis_core.protocol import ToolRequest, ToolResult


class SQLiteMemoryEngine:
    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        if self.db_path != ":memory:":
            path = Path(self.db_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = str(path.absolute())

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS tool_calls (
                call_id TEXT PRIMARY KEY,
                session_id TEXT,
                tool_name TEXT,
                arguments TEXT,
                status TEXT,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
        """)

        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                interaction_id TEXT PRIMARY KEY,
                session_id TEXT,
                user_input TEXT,
                ai_response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
        """)

        self._conn.commit()

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO sessions (session_id) VALUES (?)", (session_id,)
        )
        self._conn.commit()
        return session_id

    def record_tool_call(
        self, session_id: str, request: ToolRequest, result: ToolResult
    ) -> str:
        call_id = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO tool_calls (call_id, session_id, tool_name, arguments, status, result)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                call_id,
                session_id,
                request.tool,
                json.dumps(request.arguments, default=str),
                result.status,
                json.dumps(result.data, default=str) if result.data else None,
            ),
        )
        self._conn.commit()
        return call_id

    def record_interaction(
        self, session_id: str, user_input: str, ai_response: str
    ) -> str:
        interaction_id = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO interactions (interaction_id, session_id, user_input, ai_response)
            VALUES (?, ?, ?, ?)
            """,
            (interaction_id, session_id, user_input, ai_response),
        )
        self._conn.commit()
        return interaction_id
