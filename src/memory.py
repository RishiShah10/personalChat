"""Persistent conversation memory backed by SQLite + Chroma vector store."""

import json
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .embedding import chunk_text, embed, init_chroma


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Memory:
    def __init__(self, directory, api_key: Optional[str] = None):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self._db_path = directory / "history.db"
        self._session_id = str(uuid.uuid4())
        self._session_created = False
        self._api_key = api_key  # passed through to embed() calls

        self._conn = self._open_connection()
        self._setup_schema()

        # Chroma lives alongside the SQLite DB in the same directory
        self._chroma = init_chroma(directory)

        jsonl_path = directory / "history.jsonl"
        if jsonl_path.exists():
            self._migrate_jsonl(jsonl_path)

    def _open_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _handle_corruption(self):
        """Rename corrupt DB and open a fresh one."""
        corrupt_path = self._db_path.with_suffix(".db.corrupt")
        print(f"\nWarning: database is corrupted. Renaming to {corrupt_path.name} and starting fresh.")
        print("Your previous history may be recoverable from that file.\n")
        try:
            self._conn.close()
        except Exception:
            pass
        if self._db_path.exists():
            shutil.move(str(self._db_path), str(corrupt_path))
        self._conn = self._open_connection()
        self._session_id = str(uuid.uuid4())
        self._session_created = False
        self._setup_schema()

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

        try:
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
        except sqlite3.DatabaseError:
            print("Warning: your last message was not saved — the database may be corrupted.")
            print("Try sending it again. If this keeps happening, restart the app.\n")
            return
        except sqlite3.OperationalError:
            self._handle_corruption()
            return

        # Chunk + embed after successful SQLite write
        self._store_embeddings(msg_id, role, content)

    def _store_embeddings(self, msg_id: str, role: str, content: str):
        """Chunk message, embed each chunk, store in Chroma."""
        chunks = chunk_text(content)
        for i, chunk in enumerate(chunks):
            try:
                vector = embed(chunk, api_key=self._api_key)
                self._chroma.add(
                    ids=[f"{msg_id}_chunk_{i}"],
                    embeddings=[vector],
                    documents=[chunk],
                    # metadata lets us filter by session so RAG stays session-scoped
                    metadatas=[{"session_id": self._session_id, "role": role, "chunk_index": i, "message_id": msg_id}],
                )
            except Exception as e:
                # Embedding failure is non-fatal — SQLite already has the message
                print(f"Warning: could not embed chunk {i} of message — {e}")

    def get_relevant(self, query: str, n: int = 5) -> list:
        """Find top-n similar chunks, then fetch their full messages from SQLite."""
        try:
            query_vector = embed(query, api_key=self._api_key)
            results = self._chroma.query(
                query_embeddings=[query_vector],
                n_results=n,
                where={"session_id": self._session_id},  # stay within current session
            )

            # Collect unique message IDs from the matched chunks
            message_ids = list({meta["message_id"] for meta in results["metadatas"][0]})

            if not message_ids:
                return []

            # Fetch full messages from SQLite using those IDs
            placeholders = ",".join("?" * len(message_ids))
            rows = self._conn.execute(
                f"SELECT id, role, content FROM messages WHERE id IN ({placeholders}) ORDER BY created_at ASC",
                message_ids,
            ).fetchall()

            return [dict(r) for r in rows]
        except Exception as e:
            # RAG failure is non-fatal — fall back to sliding window only
            print(f"Warning: RAG retrieval failed — {e}")
            return []

    def get_history(self) -> list:
        # TODO: need deep dive — locked DB (OperationalError with "locked") should retry, not trigger corruption handling
        try:
            rows = self._conn.execute(
                "SELECT id, role, content, created_at FROM messages ORDER BY created_at ASC",
            ).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.DatabaseError:
            self._handle_corruption()
            return []

    def get_recent(self, n: int = 20) -> list:
        # TODO: need deep dive — locked DB (OperationalError with "locked") should retry, not trigger corruption handling
        try:
            rows = self._conn.execute(
                "SELECT id, role, content FROM messages WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
                (self._session_id, n),
            ).fetchall()
            return [dict(r) for r in reversed(rows)]
        except sqlite3.DatabaseError:
            self._handle_corruption()
            return []

    def list_sessions(self) -> list:
        # TODO: need deep dive — locked DB (OperationalError with "locked") should retry, not trigger corruption handling
        try:
            rows = self._conn.execute(
                "SELECT id, created_at, message_count, preview FROM sessions ORDER BY created_at DESC",
            ).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.DatabaseError:
            self._handle_corruption()
            return []

    def resume_session(self, session_id: str) -> bool:
        row = self._conn.execute(
            "SELECT id FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        if not row:
            return False
        self._session_id = session_id
        self._session_created = True
        return True
