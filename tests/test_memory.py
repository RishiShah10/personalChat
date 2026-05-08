"""Test suite for memory system."""

import pytest
from pathlib import Path
from src.memory import Memory


@pytest.fixture
def temp_memory(tmp_path):
    """Create a Memory instance with a temporary directory."""
    memory = Memory(data_dir=str(tmp_path / ".chat_history"))
    yield memory
    memory.clear()


def test_load_empty_history(temp_memory):
    """Test that loading non-existent history returns empty list."""
    assert temp_memory.load() == []


def test_save_and_load_single_exchange(temp_memory):
    """Test that we can save and load a single exchange."""
    temp_memory.save_exchange("Hello", "Hi there!")
    history = temp_memory.load()

    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Hello"}
    assert history[1] == {"role": "agent", "content": "Hi there!"}


def test_save_multiple_exchanges(temp_memory):
    """Test that multiple exchanges are appended, not overwritten."""
    temp_memory.save_exchange("Hello", "Hi!")
    temp_memory.save_exchange("How are you?", "I'm good!")

    history = temp_memory.load()
    assert len(history) == 4
    assert history[0]["content"] == "Hello"
    assert history[1]["content"] == "Hi!"
    assert history[2]["content"] == "How are you?"
    assert history[3]["content"] == "I'm good!"


def test_clear_history(temp_memory):
    """Test that clear removes all history."""
    temp_memory.save_exchange("Hello", "Hi!")
    assert len(temp_memory.load()) == 2

    temp_memory.clear()
    assert temp_memory.load() == []


def test_persistence_across_instances(temp_memory):
    """Test that history persists across Memory instances."""
    temp_memory.save_exchange("First message", "Response 1")

    # Create new instance with same data dir
    memory2 = Memory(data_dir=temp_memory.data_dir)
    history = memory2.load()

    assert len(history) == 2
    assert history[0]["content"] == "First message"


def test_get_context_max_messages(temp_memory):
    """Test that get_context respects max_messages limit."""
    for i in range(5):
        temp_memory.save_exchange(f"Message {i}", f"Response {i}")

    history = temp_memory.load()
    context = temp_memory.get_context(history, max_messages=4)

    # Should only include last 4 messages (2 exchanges)
    assert "Message 3" in context
    assert "Message 0" not in context


def test_save_preserves_existing_history(temp_memory):
    """Test that save() doesn't lose existing data."""
    temp_memory.save_exchange("Message 1", "Response 1")

    history = temp_memory.load()
    history.append({"role": "user", "content": "Message 2"})
    temp_memory.save(history)

    reloaded = temp_memory.load()
    assert len(reloaded) == 3
    assert reloaded[-1]["content"] == "Message 2"


def test_message_format(temp_memory):
    """Test that messages have correct format."""
    temp_memory.save_exchange("Test", "Response")
    history = temp_memory.load()

    for msg in history:
        assert "role" in msg
        assert "content" in msg
        assert msg["role"] in ["user", "agent"]
        assert isinstance(msg["content"], str)
