# CLI Chat Agent with Memory

## Problem Brief

Build a CLI chat agent that:
1. Accepts user messages in an interactive loop
2. Responds to those messages 
3. **Persists conversation history to disk and reloads it on startup**

The focus is on the **memory system** — how you design it, persist it, and manage it.

## Requirements

- [ ] CLI interface: read user input, show agent responses
- [ ] Load conversation history from disk on startup
- [ ] Save new messages to disk after each exchange
- [ ] Pass the test suite

## Getting Started

```bash
uv sync
uv run pytest tests/
```

The tests define what "correct" means. Make them pass.

## Notes

- Keep it simple. Don't over-engineer.
- The test harness is your spec.
- You can use anything in the stdlib. External deps are fine if you justify them.
