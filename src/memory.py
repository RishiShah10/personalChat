"""Persistent conversation memory backed by SQLite."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Memory:
    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self._db_path = directory / "history.db"
        self._session_id = str(uuid.uuid4())
        self._session_created = False

        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._setup_schema()

        jsonl_path = directory / "history.jsonl"
        if jsonl_path.exists():
            self._migrate_jsonl(jsonl_path)

    def _setup_schema(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id            TEXT PRIMARY KEY,
                created_at    TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                preview       TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, created_at);
        """)
        self._conn.commit()

    def _migrate_jsonl(self, jsonl_path: Path):
        messages = []
        try:
            with open(jsonl_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        messages.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            print(f"Warning: could not migrate {jsonl_path} — skipping.")
            return

        if not messages:
            jsonl_path.rename(jsonl_path.with_suffix(".jsonl.bak"))
            return

        migrated_id = str(uuid.uuid4())
        preview = next(
            (m.get("content", "") for m in messages if m.get("role") == "user"), ""
        )
        now = _now()

        with self._conn:
            self._conn.execute(
                "INSERT INTO sessions(id, created_at, message_count, preview) VALUES (?,?,?,?)",
                (migrated_id, now, len(messages), preview[:120]),
            )
            for msg in messages:
                self._conn.execute(
                    "INSERT INTO messages(id, session_id, role, content, created_at) VALUES (?,?,?,?,?)",
                    (
                        msg.get("id", str(uuid.uuid4())),
                        migrated_id,
                        msg.get("role", "user"),
                        msg.get("content", ""),
                        now,
                    ),
                )

        jsonl_path.rename(jsonl_path.with_suffix(".jsonl.bak"))
        print(f"Migrated existing history to SQLite ({jsonl_path.name}.bak kept as backup).")

    def _ensure_session(self, first_content: str = ""):
        if not self._session_created:
            self._conn.execute(
                "INSERT INTO sessions(id, created_at, message_count, preview) VALUES (?,?,?,?)",
                (self._session_id, self._session_created or _now(), 0, first_content[:120]),
            )
            self._conn.commit()
            self._session_created = True

    def add_message(self, role: str, content: str):
        now = _now()
        msg_id = str(uuid.uuid4())

        with self._conn:
            if not self._session_created:
                preview = content[:120] if role == "user" else ""
                self._conn.execute(
                    "INSERT INTO sessions(id, created_at, message_count, preview) VALUES (?,?,?,?)",
                    (self._session_id, now, 0, preview),
                )
                self._session_created = True

            self._conn.execute(
                "INSERT INTO messages(id, session_id, role, content, created_at) VALUES (?,?,?,?,?)",
                (msg_id, self._session_id, role, content, now),
            )
            self._conn.execute(
                "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
                (self._session_id,),
            )

    def get_history(self) -> list:
        rows = self._conn.execute(
            "SELECT id, role, content, created_at FROM messages ORDER BY created_at ASC",
        ).fetchall()
        return [dict(r) for r in rows]

    def get_recent(self, n: int = 20) -> list:
        rows = self._conn.execute(
            "SELECT role, content FROM messages WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
            (self._session_id, n),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def list_sessions(self) -> list:
        rows = self._conn.execute(
            "SELECT id, created_at, message_count, preview FROM sessions ORDER BY created_at DESC",
        ).fetchall()
        return [dict(r) for r in rows]

    def resume_session(self, session_id: str) -> bool:
        row = self._conn.execute(
            "SELECT id FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        if not row:
            return False
        self._session_id = session_id
        self._session_created = True
        return True
