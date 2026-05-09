#!/usr/bin/env python3
"""CLI chat agent with persistent memory."""

import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from src.memory import Memory

load_dotenv()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

HISTORY_DIR = Path.home() / ".chat_agent"


def chat(messages: list) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    return response.choices[0].message.content


def handle_command(user_input: str, memory: Memory) -> bool:
    """Handle /commands. Returns True if input was a command (skip LLM call)."""
    if user_input == "/sessions":
        sessions = memory.list_sessions()
        if not sessions:
            print("No sessions found.\n")
        else:
            print(f"\n{'ID':<36}  {'Date':<20}  {'Msgs':>4}  Preview")
            print("-" * 80)
            for s in sessions:
                date = s["created_at"][:19].replace("T", " ")
                preview = (s["preview"] or "")[:30]
                print(f"{s['id']}  {date}  {s['message_count']:>4}  {preview}")
            print()
        return True

    if user_input.startswith("/resume "):
        session_id = user_input.split(" ", 1)[1].strip()
        if memory.resume_session(session_id):
            count = len(memory.get_history())
            print(f"Resumed session {session_id}. {count} messages loaded.\n")
        else:
            print(f"Session not found: {session_id}\n")
        return True

    if user_input == "/help":
        print("\nCommands:")
        print("  /sessions        — list all past sessions")
        print("  /resume <id>     — continue a past session")
        print("  quit             — exit\n")
        return True

    return False


def main():
    memory = Memory(HISTORY_DIR, api_key=os.environ["OPENAI_API_KEY"])

    print("Chat agent ready. Type /help for commands or 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if handle_command(user_input, memory):
            continue

        # Sliding window — last 20 messages for recency
        recent = memory.get_recent(20)
        recent_ids = {m["id"] for m in recent}  # message IDs already in the window

        # RAG — top 5 full messages whose chunks matched the query
        # deduplicate by id so we don't send a message already in the sliding window
        relevant = [
            m for m in memory.get_relevant(user_input, n=5)
            if m["id"] not in recent_ids
        ]

        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        if relevant:
            # Label RAG chunks clearly so the model knows they're retrieved context
            messages.append({
                "role": "system",
                "content": "Relevant context from earlier in the conversation:\n" +
                           "\n".join(f"[{m['role']}]: {m['content']}" for m in relevant)
            })
        messages += [{"role": m["role"], "content": m["content"]} for m in recent]
        messages.append({"role": "user", "content": user_input})

        reply = chat(messages)

        memory.add_message("user", user_input)
        memory.add_message("assistant", reply)

        print(f"Agent: {reply}\n")


if __name__ == "__main__":
    main()
