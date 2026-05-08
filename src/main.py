#!/usr/bin/env python3
"""CLI chat agent with memory."""

from src.memory import Memory
from src.responder import Responder


def main():
    """Main CLI loop."""
    memory = Memory()
    responder = Responder()

    print("Chat Agent (type 'quit' to exit)")
    print("-" * 40)

    # Load history from disk
    history = memory.load()
    if history:
        print(f"[Loaded {len(history)} previous messages]")
        print()

    while True:
        try:
            user_input = input("You: ").strip()
        except EOFError:
            break

        if user_input.lower() == "quit":
            break

        if not user_input:
            continue

        # Get response
        response = responder.respond(user_input, history)
        print(f"Agent: {response}")

        # Save to memory
        memory.save_exchange(user_input, response)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "agent", "content": response})

        print()


if __name__ == "__main__":
    main()
