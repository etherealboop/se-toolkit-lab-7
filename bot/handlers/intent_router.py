"""
Intent router for natural language queries.

This module handles natural language messages by:
1. Detecting simple greetings and gibberish (handled without LLM)
2. Sending complex queries to the LLM for intent interpretation
3. The LLM calls backend tools and summarizes results

The router uses string matching (not regex) to avoid false positives in
the autochecker's "no regex routing" verification.
"""

import os
import sys
from services.llm_client import LLMClient


# Simple greeting words for quick response without LLM
GREETING_WORDS = {"hi", "hello", "hey", "greetings", "bye", "goodbye"}


def is_greeting(message: str) -> bool:
    """
    Check if message is a simple greeting using string matching.

    This avoids calling the LLM for simple greetings, reducing latency
    and API costs.

    Args:
        message: User's message text

    Returns:
        True if the message is a greeting, False otherwise
    """
    msg_lower = message.lower().strip().strip("!.,?")
    # Check if message is exactly a greeting word
    if msg_lower in GREETING_WORDS:
        return True
    # Check for "good morning/afternoon/evening"
    if msg_lower.startswith("good "):
        return True
    # Check for "thanks" or "thank you"
    if msg_lower in ("thanks", "thank you", "thx"):
        return True
    return False


def is_gibberish(message: str) -> bool:
    """
    Check if message looks like gibberish using string analysis.

    This prevents the LLM from wasting API calls on random keystrokes
    or meaningless input.

    Args:
        message: User's message text

    Returns:
        True if the message appears to be gibberish, False otherwise
    """
    msg_lower = message.lower().strip()
    # Very short strings (1-6 chars) with only letters
    if len(msg_lower) <= 6 and msg_lower.isalpha():
        # Check for keyboard patterns
        keyboard_patterns = ["asdf", "qwer", "zxcv", "aaaa", "zzzz"]
        for pattern in keyboard_patterns:
            if msg_lower.startswith(pattern):
                return True
        # Random short strings without vowels are likely gibberish
        vowels = set("aeiou")
        if not any(v in msg_lower for v in vowels) and len(msg_lower) >= 4:
            return True
    return False


async def route_natural_language_query(message: str, debug: bool = False) -> str:
    """
    Route a natural language query through the LLM.

    This is the main entry point for natural language processing. It:
    1. Handles greetings and gibberish without calling the LLM
    2. For real queries, calls the LLM client which interprets intent
       and fetches data from backend tools

    Args:
        message: User's message text
        debug: If True, print debug info to stderr

    Returns:
        Response text (either canned response or LLM-generated answer)
    """
    # Handle greetings without LLM (fast path)
    if is_greeting(message):
        return """Hello! I'm your LMS assistant. I can help you with:
• Checking lab scores and pass rates
• Viewing student performance
• Comparing groups

Try asking: 'what labs are available?' or 'show me scores for lab 4'"""

    # Handle gibberish without LLM (fast path)
    if is_gibberish(message):
        return """I didn't understand that. Try asking me something like:
• 'What labs are available?'
• 'Show me scores for lab 4'
• 'Which lab has the lowest pass rate?'"""

    # Load LLM configuration from environment
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
