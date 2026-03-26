"""
Command handlers for the LMS Telegram bot.

Handlers are plain functions that take input and return text.
They don't depend on Telegram — same function works from --test mode,
unit tests, or Telegram.
"""


async def handle_start(user_id: int) -> str:
    """Handle /start command."""
    return "Welcome! Use /help to see available commands."


async def handle_help(user_id: int) -> str:
    """Handle /help command."""
    return "Available commands: /start, /help, /health, /labs, /scores"


async def handle_health(user_id: int) -> str:
    """Handle /health command."""
    return "Backend status: OK"


async def handle_labs(user_id: int) -> str:
    """Handle /labs command."""
    return "Available labs: lab-01, lab-02, lab-03, lab-04"


async def handle_scores(user_id: int, lab: str | None = None) -> str:
    """Handle /scores command."""
    if lab:
        return f"Scores for {lab}: 85/100"
    return "Your average score: 85/100"
