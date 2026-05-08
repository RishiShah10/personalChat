# CLI Chat Agent with Memory

## Project Brief

Build a CLI chat agent that can:
1. Accept user messages in an interactive loop
2. Respond to those messages (rule-based or API-driven)
3. **Persist conversation history** to disk and reload it on startup
4. **Implement a memory system** that decides what to keep, summarize, or discard

### Requirements

**Core (Must-Have)**
- [ ] CLI interface: read user input, show agent responses
- [ ] Load conversation history from disk on startup
- [ ] Save new messages to disk after each exchange
- [ ] Pass the test suite (see `tests/test_memory.py`)

**Memory System (Core Design Problem)**
- Decide how to represent conversation state (structure, serialization)
- Implement a strategy for managing memory (full history? summaries? context windows?)
- Think about edge cases: large conversations, token limits, data loss

**Nice-to-Have (if time)**
- Token counting to estimate conversation size
- Summarization strategy (when to summarize old messages?)
- Conversation pruning (max history depth, age-based eviction)
- Configuration for memory behavior

### Architecture Notes

- Use a simple rule-based responder for now (or call Claude API if you have a key)
- Focus on the **memory system**, not the AI model
- The test harness will validate that memory works correctly
- Think about: what goes wrong if the process crashes? If history grows unbounded?

## Getting Started

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Run the CLI:**
   ```bash
   uv run src/main.py
   ```

3. **Run tests:**
   ```bash
   uv run pytest tests/
   ```

4. **Example session:**
   ```
   > Hello
   Agent: Hi there! How can I help?
   > What's my name?
   Agent: You haven't told me your name yet.
   > I'm Alice
   Agent: Nice to meet you, Alice!
   ```

## What We're Looking For

1. **Memory System Design** — how you think about persistence, state management, edge cases
2. **Code Taste** — clear structure, reasonable abstractions, no over-engineering
3. **Testing** — how you verify your memory system actually works
4. **Walkthrough** — at the end, clearly explain what you built and why

You don't need to implement everything. Focus on getting core + memory working well, then we'll talk through what you'd do next.

---

**Time Budget:** 60 minutes
**Starter Code:** Basic CLI loop + test harness included
**Problem Brief:** You're reading it now!
