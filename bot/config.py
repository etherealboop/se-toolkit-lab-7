"""
Configuration loader for the bot.

Reads environment variables from .env.bot.secret file using python-dotenv.
This allows the bot to access secrets (bot token, API keys) without hardcoding them.

Environment variables loaded:
    BOT_TOKEN: Telegram bot token from @BotFather
    LMS_API_URL: Base URL of the LMS backend API
    LMS_API_KEY: API key for authenticating with the backend
    LLM_API_KEY: API key for the LLM service (Qwen Code)
    LLM_API_BASE_URL: Base URL of the LLM API
    LLM_API_MODEL: Model name to use for LLM queries
"""

import os
from dotenv import load_dotenv
from pathlib import Path

def load_config() -> dict[str, str]:
    """
    Load configuration from .env.bot.secret file.

    The function searches for the .env.bot.secret file in:
    1. The bot directory (bot/.env.bot.secret)
    2. The parent directory (.env.bot.secret)

    This flexibility allows the bot to work both when run from the bot directory
    and when run from the repo root.

    Returns:
        Dictionary with config values:
        - BOT_TOKEN: Telegram bot authentication token
        - LMS_API_URL: Backend API base URL
        - LMS_API_KEY: Backend API authentication key
        - LLM_API_KEY: LLM API authentication key
        - LLM_API_BASE_URL: LLM API base URL
        - LLM_API_MODEL: LLM model identifier
    """
    # Find .env.bot.secret in the bot directory
    bot_dir = Path(__file__).parent
    env_file = bot_dir / ".env.bot.secret"

    # Load environment variables from file
    if env_file.exists():
        load_dotenv(env_file)
    else:
        # Try parent directory (for when bot is run from repo root)
        parent_env = bot_dir.parent / ".env.bot.secret"
        if parent_env.exists():
            load_dotenv(parent_env)

    return {
        "BOT_TOKEN": os.getenv("BOT_TOKEN", ""),
        "LMS_API_URL": os.getenv("LMS_API_URL", ""),
        "LMS_API_KEY": os.getenv("LMS_API_KEY", ""),
        "LLM_API_KEY": os.getenv("LLM_API_KEY", ""),
        "LLM_API_BASE_URL": os.getenv("LLM_API_BASE_URL", ""),
        "LLM_API_MODEL": os.getenv("LLM_API_MODEL", ""),
    }
