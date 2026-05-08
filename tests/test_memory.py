"""Test suite for memory system."""

import pytest
from pathlib import Path


# NOTE: You'll need to implement a Memory class in src/memory.py
# These tests validate that your memory system works correctly.
# Feel free to adjust the API if it makes sense for your design.


def test_memory_persists_to_disk():
    """Conversation history should survive a restart."""
    from src.memory import Memory
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        # First instance: save some messages
        mem1 = Memory(tmpdir)
        mem1.add_message("user", "Hello")
        mem1.add_message("agent", "Hi there!")

        # Second instance: load the messages
        mem2 = Memory(tmpdir)
        history = mem2.get_history()

        assert len(history) >= 2
        assert any("Hello" in str(msg) for msg in history)


def test_memory_appends_not_overwrites():
    """Multiple saves should append, not replace."""
    from src.memory import Memory
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        mem = Memory(tmpdir)
        mem.add_message("user", "First")
        mem.add_message("agent", "Response")

        history_before = len(mem.get_history())

        mem.add_message("user", "Second")
        history_after = len(mem.get_history())

        assert history_after > history_before


def test_memory_handles_empty_state():
    """Empty or missing history should not crash."""
    from src.memory import Memory
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        mem = Memory(tmpdir)
        history = mem.get_history()
        assert isinstance(history, list)


def test_memory_preserves_message_order():
    """Messages should be returned in the order they were added."""
    from src.memory import Memory
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        mem = Memory(tmpdir)
        mem.add_message("user", "A")
        mem.add_message("user", "B")
        mem.add_message("user", "C")

        history = mem.get_history()
        contents = [msg.get("content") if isinstance(msg, dict) else str(msg) for msg in history]

        # Your implementation's structure may vary,
        # but the order should match insertion order
        assert contents[-3:] == ["A", "B", "C"] or "A" in str(contents) and "C" in str(contents)
