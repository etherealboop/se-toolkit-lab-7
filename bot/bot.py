#!/usr/bin/env python3
"""
Telegram bot entry point with --test mode.

Usage:
    uv run bot.py --test "/start"    # Test mode, no Telegram connection
    uv run bot.py                    # Normal mode, connects to Telegram
"""

import argparse
import sys

from handlers import (
    handle_start,
    handle_help,
    handle_health,
    handle_labs,
    handle_scores,
)
from config import load_config


def get_handler_for_command(command: str):
    """
    Route command to the appropriate handler.

    Returns: (handler_function, args_dict)
    """
    command = command.strip()

    if command == "/start":
        return handle_start, {"user_id": 0}
    elif command == "/help":
        return handle_help, {"user_id": 0}
    elif command == "/health":
        return handle_health, {"user_id": 0}
    elif command == "/labs":
        return handle_labs, {"user_id": 0}
    elif command.startswith("/scores"):
        parts = command.split(maxsplit=1)
        lab = parts[1] if len(parts) > 1 else None
        return handle_scores, {"user_id": 0, "lab": lab}
    else:
        return None, {}


def run_test_mode(command: str) -> None:
    """Run a command in test mode and print result to stdout."""
    import asyncio

    handler, kwargs = get_handler_for_command(command)

    if handler is None:
        print(f"Unknown command: {command}")
        sys.exit(1)

    result = asyncio.run(handler(**kwargs))
    print(result)
    sys.exit(0)


def run_telegram_mode() -> None:
    """Run the bot in Telegram mode (connects to Telegram API)."""
    config = load_config()

    if not config["BOT_TOKEN"]:
        print("Error: BOT_TOKEN not set. Create .env.bot.secret with your bot token.")
        sys.exit(1)

    print("Telegram mode not implemented yet — coming in Task 2")
    sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(description="LMS Telegram Bot")
    parser.add_argument(
        "--test",
        type=str,
        metavar="COMMAND",
        help="Test mode: run a command and print result (e.g., '/start')",
    )

    args = parser.parse_args()

    if args.test:
        run_test_mode(args.test)
    else:
        run_telegram_mode()


if __name__ == "__main__":
    main()
