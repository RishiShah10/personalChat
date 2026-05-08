"""Memory system for the chat agent."""

import json
import os
from pathlib import Path
from typing import Any, List


class Memory:
    """Manages conversation history persistence."""

    def __init__(self, data_dir: str = ".chat_history"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.history_file = self.data_dir / "history.json"

    def load(self) -> List[dict]:
        """Load conversation history from disk.

        Returns: List of messages in format [{"role": "user"|"agent", "content": "..."}, ...]
        """
        if not self.history_file.exists():
            return []

        try:
            with open(self.history_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def save(self, history: List[dict]) -> None:
        """Save full conversation history to disk."""
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2)

    def save_exchange(self, user_input: str, agent_response: str) -> None:
        """Save a single user->agent exchange to disk.

        This should append to existing history, not overwrite.
        """
        history = self.load()
        history.append({"role": "user", "content": user_input})
        history.append({"role": "agent", "content": agent_response})
        self.save(history)

    def clear(self) -> None:
        """Clear all history (useful for testing)."""
        if self.history_file.exists():
            self.history_file.unlink()

    def get_context(self, history: List[dict], max_messages: int = 10) -> str:
        """Get a context string from recent history.

        TODO: Think about how to summarize or truncate large conversations.
        """
        recent = history[-max_messages:]
        return "\n".join(
            f"{msg['role']}: {msg['content']}" for msg in recent
        )
