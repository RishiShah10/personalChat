"""Persistent conversation memory backed by JSONL on disk."""

import fcntl
import json
import uuid
from pathlib import Path


class Memory:
    def __init__(self, directory):
        self._path = Path(directory) / "history.jsonl"
        self._messages = self._load()

    def _load(self):
        if not self._path.exists():
            return []
        messages = []
        try:
            with open(self._path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        messages.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            print(
                f"Warning: history file corrupted ({self._path}). "
                "Starting fresh and deleting corrupted file."
            )
            self._path.unlink()
            return []
        return messages

    def add_message(self, role, content):
        msg = {"id": str(uuid.uuid4()), "role": role, "content": content}
        self._messages.append(msg)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(json.dumps(msg) + "\n")
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def get_history(self):
        return list(self._messages)

    def get_recent(self, n=20):
        return self._messages[-n:]
