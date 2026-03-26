"""
Configuration loader for the bot.

Reads environment variables from .env.bot.secret file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def load_config() -> dict[str, str]:
    """
    Load configuration from .env.bot.secret file.
    
    Returns:
        Dictionary with config values:
        - BOT_TOKEN
        - LMS_API_URL
        - LMS_API_KEY
        - LLM_API_KEY
        - LLM_API_BASE_URL
        - LLM_API_MODEL
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
