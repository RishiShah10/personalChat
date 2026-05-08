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


def main():
    memory = Memory(HISTORY_DIR)

    print("Chat agent ready. Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            break

        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        messages += [
            {"role": m["role"], "content": m["content"]}
            for m in memory.get_recent(20)
        ]
        messages.append({"role": "user", "content": user_input})

        reply = chat(messages)

        memory.add_message("user", user_input)
        memory.add_message("assistant", reply)

        print(f"Agent: {reply}\n")


if __name__ == "__main__":
    main()
