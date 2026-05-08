"""Simple rule-based responder."""

from typing import List


class Responder:
    """Generates responses based on message history."""

    def respond(self, user_input: str, history: List[dict]) -> str:
        """Generate a response to user input."""
        lower = user_input.lower()

        # Rule-based patterns
        if "hello" in lower or "hi " in lower:
            return "Hi there! How can I help?"
        elif "what's my name" in lower or "who am i" in lower:
            return self._extract_name(history) or "You haven't told me your name yet."
        elif "what did i say" in lower or "history" in lower:
            return self._summarize_history(history)
        else:
            return "That's interesting. Tell me more."

    def _extract_name(self, history: List[dict]) -> str:
        """Extract user's name from history if mentioned."""
        for msg in history:
            if msg.get("role") == "user":
                text = msg.get("content", "").lower()
                if "i'm " in text or "i am " in text:
                    # Simple extraction: "I'm Alice" -> "Alice"
                    for phrase in ["i'm ", "i am "]:
                        if phrase in text:
                            name = text.split(phrase)[1].split()[0].rstrip(".")
                            return f"Your name is {name}!"
        return ""

    def _summarize_history(self, history: List[dict]) -> str:
        """Summarize conversation history."""
        if not history:
            return "We haven't talked yet."
        return f"We've had {len(history)} messages in our conversation."
