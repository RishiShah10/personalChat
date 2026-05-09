# Project Description

A CLI chat agent with persistent, session-aware conversation memory.

## What it does

The agent accepts natural-language input from the user, sends it to OpenAI's GPT-4o-mini, and streams the reply back to the terminal. Every exchange is persisted to a local SQLite database so conversations survive restarts. Each run starts a new session by default; past sessions can be listed and resumed from the command line.

## Key components

| File | Role |
|------|------|
| `src/main.py` | Entry point — REPL loop, command dispatch, OpenAI API calls |
| `src/memory.py` | `Memory` class — SQLite-backed storage with session isolation, JSONL migration, and corruption recovery |
| `tests/test_memory.py` | Unit tests for the `Memory` class |

## Runtime data

The agent stores its database at `~/.chat_agent/history.db` (outside the repo). No conversation data is committed to git.

## CLI commands

| Command | Description |
|---------|-------------|
| `/sessions` | List all past sessions |
| `/resume <id>` | Load and continue a previous session |
| `/help` | Show available commands |
| `quit` | Exit the agent |

## Setup

```bash
cp .env.example .env   # add your OPENAI_API_KEY
uv sync
uv run python -m src.main
```

## Tech stack

- Python 3.8+
- OpenAI Python SDK (`gpt-4o-mini`)
- SQLite (via stdlib `sqlite3`, WAL mode)
- `uv` for dependency management
- `pytest` for tests
