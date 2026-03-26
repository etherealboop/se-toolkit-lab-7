"""
Command handlers for the LMS Telegram bot.

Handlers are plain functions that take input and return text.
They don't depend on Telegram — same function works from --test mode,
unit tests, or Telegram.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from services.lms_client import LMSClient

# Load environment variables from .env.bot.secret
bot_dir = Path(__file__).parent.parent
env_file = bot_dir / ".env.bot.secret"
if env_file.exists():
    load_dotenv(env_file)


def _get_lms_client() -> LMSClient:
    """Create LMS client from environment variables."""
    import os

    base_url = os.getenv("LMS_API_URL", "http://localhost:42002")
    api_key = os.getenv("LMS_API_KEY", "")
    return LMSClient(base_url, api_key)


async def handle_start(user_id: int) -> str:
    """Handle /start command."""
    return "Welcome! Use /help to see available commands."


async def handle_help(user_id: int) -> str:
    """Handle /help command."""
    return """Available commands:
/start — Welcome message
/help — List all commands
/health — Check backend status
/labs — List available labs
/scores <lab> — Get pass rates for a lab (e.g., /scores lab-04)"""


async def handle_health(user_id: int) -> str:
    """Handle /health command."""
    client = _get_lms_client()
    try:
        result = await client.get_health()
        if result["healthy"]:
            return f"Backend is healthy. {result['items_count']} items available."
        else:
            return f"Backend error: {result['error']}. Check that the services are running."
    finally:
        await client.close()


async def handle_labs(user_id: int) -> str:
    """Handle /labs command."""
    client = _get_lms_client()
    try:
        result = await client.get_labs()
        if "error" in result:
            return f"Backend error: {result['error']}. Check that the services are running."

        labs = result.get("labs", [])
        if not labs:
            return "No labs available."

        lines = ["Available labs:"]
        for lab in labs:
            lines.append(f"- {lab['id']} — {lab['name']}")
        return "\n".join(lines)
    finally:
        await client.close()


async def handle_scores(user_id: int, lab: str | None = None) -> str:
    """Handle /scores command."""
    if not lab:
        return "Usage: /scores <lab> (e.g., /scores lab-04)"

    client = _get_lms_client()
    try:
        result = await client.get_pass_rates(lab)
        if "error" in result:
            return (
                f"Backend error: {result['error']}. Check that the lab ID is correct."
            )

        pass_rates = result.get("pass_rates", [])
        if not pass_rates:
            return f"No pass rates found for {lab}."

        lines = [f"Pass rates for {lab}:"]
        for task in pass_rates:
            task_name = task.get(
                "task", task.get("task_name", task.get("task_id", "Unknown"))
            )
            pass_rate = task.get("avg_score", task.get("pass_rate", 0))
            attempts = task.get("attempts", 0)
            lines.append(f"- {task_name}: {pass_rate:.1f}% ({attempts} attempts)")
        return "\n".join(lines)
    finally:
        await client.close()


async def handle_unknown(user_id: int, command: str) -> str:
    """Handle unknown commands."""
    return f"Unknown command: {command}. Use /help to see available commands."
