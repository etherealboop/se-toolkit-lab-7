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
from handlers.intent_router import route_natural_language_query

# Load environment variables from .env.bot.secret
bot_dir = Path(__file__).parent.parent
env_file = bot_dir / ".env.bot.secret"
if env_file.exists():
    load_dotenv(env_file)


def _get_lms_client() -> LMSClient:
    """Create LMS client from environment variables."""
    base_url = os.getenv("LMS_API_URL", "http://localhost:42002")
    api_key = os.getenv("LMS_API_KEY", "")
    return LMSClient(base_url, api_key)


# Inline keyboard buttons for common actions
KEYBOARD_BUTTONS = [
    [{"text": "📊 Labs", "callback_data": "labs"}],
    [{"text": "💚 Health", "callback_data": "health"}],
    [{"text": "📈 Scores lab-4", "callback_data": "scores_lab-4"}],
    [{"text": "🏆 Top learners", "callback_data": "top_learners"}],
    [{"text": "❓ Help", "callback_data": "help"}],
]


def get_keyboard_markup():
    """Get inline keyboard markup for Telegram."""
    from aiogram.types import InlineKeyboardMarkup
    from aiogram.types import InlineKeyboardButton

    keyboard = []
    for row in KEYBOARD_BUTTONS:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=btn["text"], callback_data=btn["callback_data"]
                )
                for btn in row
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def handle_start(user_id: int) -> str:
    """Handle /start command."""
    return """Welcome to the LMS Bot!

I can help you check lab scores, pass rates, and student performance.

Try asking me questions like:
• "What labs are available?"
• "Show me scores for lab 4"
• "Which lab has the lowest pass rate?"
• "Who are the top 5 students?"

Use /help to see all commands."""


async def handle_help(user_id: int) -> str:
    """Handle /help command."""
    return """Available commands:
/start — Welcome message
/help — List all commands
/health — Check backend status
/labs — List available labs
/scores <lab> — Get pass rates for a lab (e.g., /scores lab-04)

You can also ask me questions in natural language:
• "What labs are available?"
• "Show me scores for lab 4"
• "Which lab has the lowest pass rate?"
• "Who are the top 5 students in lab 4?"
• "How many students are enrolled?"
• "Compare groups in lab 3\""""


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


async def handle_natural_language(message: str, debug: bool = False) -> str:
    """
    Handle natural language queries via LLM.

    Args:
        message: User's message text
        debug: If True, print debug info to stderr

    Returns:
        Response from LLM
    """
    return await route_natural_language_query(message, debug)


async def handle_unknown(user_id: int, command: str) -> str:
    """Handle unknown commands."""
    return f"Unknown command: {command}. Use /help to see available commands."
