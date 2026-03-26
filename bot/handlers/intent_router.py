"""
Intent router for natural language queries.

Uses LLM to interpret user messages and call appropriate backend tools.
"""

import os
import sys
from services.llm_client import LLMClient


async def route_natural_language_query(message: str, debug: bool = False) -> str:
    """
    Route a natural language query through the LLM.

    Args:
        message: User's message text
        debug: If True, print debug info to stderr

    Returns:
        Response text
    """
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
