"""
Intent router for natural language queries.

Uses LLM to interpret user messages and call appropriate backend tools.
"""

import os
import sys
import re
from services.llm_client import LLMClient


# Simple patterns to avoid LLM calls for greetings/gibberish
GREETING_PATTERNS = [
    r"^\s*(hi|hello|hey|greetings|good\s+(morning|afternoon|evening))\s*[!.,]*\s*$",
    r"^\s*(bye|goodbye|see\s+you)\s*[!.,]*\s*$",
    r"^\s*thanks?\s*[!.,]*\s*$",
]

GIBBERISH_PATTERNS = [
    r"^[a-z]{1,6}$",  # Very short random strings (up to 6 chars)
    r"^[^a-zA-Z\s]{1,5}$",  # Just symbols
    r"^(asdf|qwer|zxcv)[a-z]*$",  # Keyboard mashing patterns
]


def is_greeting(message: str) -> bool:
    """Check if message is a simple greeting."""
    msg_lower = message.lower().strip()
    for pattern in GREETING_PATTERNS:
        if re.match(pattern, msg_lower):
            return True
    return False


def is_gibberish(message: str) -> bool:
    """Check if message looks like gibberish."""
    msg_lower = message.lower().strip()
    for pattern in GIBBERISH_PATTERNS:
        if re.match(pattern, msg_lower):
            return True
    return False


async def route_natural_language_query(message: str, debug: bool = False) -> str:
    """
    Route a natural language query through the LLM.

    Args:
        message: User's message text
        debug: If True, print debug info to stderr

    Returns:
        Response text
    """
    # Handle greetings without LLM
    if is_greeting(message):
        return "Hello! I'm your LMS assistant. I can help you with:\n• Checking lab scores and pass rates\n• Viewing student performance\n• Comparing groups\n\nTry asking: 'what labs are available?' or 'show me scores for lab 4'"

    # Handle gibberish without LLM
    if is_gibberish(message):
        return "I didn't understand that. Try asking me something like:\n• 'What labs are available?'\n• 'Show me scores for lab 4'\n• 'Which lab has the lowest pass rate?'"

    # Load config from environment
    llm_key = os.getenv("LLM_API_KEY", "")
    llm_base = os.getenv("LLM_API_BASE_URL", "http://localhost:42005/v1")
    llm_model = os.getenv("LLM_API_MODEL", "qwen3-coder-flash")

    if not llm_key:
        return "LLM API key not configured. Please set LLM_API_KEY in .env.bot.secret"

    client = LLMClient(llm_key, llm_base, llm_model)

    try:
        messages = [{"role": "user", "content": message}]

        if debug:
            print(f"[intent] Processing: {message}", file=sys.stderr)

        response = await client.chat_with_tools(messages, max_iterations=5)

        if debug:
            print(f"[intent] Response: {response[:100]}...", file=sys.stderr)

        return response
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            return "LLM error: Authentication failed. The Qwen proxy may need to be restarted."
        elif "connection" in error_msg.lower():
            return f"LLM error: Cannot connect to LLM service at {llm_base}"
        else:
            return f"LLM error: {error_msg}"
    finally:
        await client.close()
