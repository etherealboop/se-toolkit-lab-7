#!/usr/bin/env python3
"""
Telegram bot entry point with --test mode.

This is the main entry point for the LMS Telegram bot. It supports two modes:
- Test mode: Run commands locally without Telegram connection (--test flag)
- Telegram mode: Connect to Telegram API and poll for messages

Usage:
    uv run bot.py --test "/start"           # Test mode, slash command
    uv run bot.py --test "what labs..."     # Test mode, natural language
    uv run bot.py                           # Normal mode, connects to Telegram

Architecture:
    The bot uses a handler pattern where command logic is separated from the
    transport layer (Telegram). This allows the same handlers to work in both
    test mode and Telegram mode.
"""

import argparse
import sys

from handlers import (
    handle_start,
    handle_help,
    handle_health,
    handle_labs,
    handle_scores,
    handle_unknown,
    handle_natural_language,
)
from config import load_config


def is_natural_language_query(text: str) -> bool:
    """
    Check if the input is a natural language query (not a slash command).

    Natural language queries don't start with "/" and are processed by the LLM
    intent router instead of the command handler.

    Args:
        text: User input text

    Returns:
        True if the input is a natural language query, False if it's a slash command
    """
    text = text.strip()
    return not text.startswith("/")


def get_handler_for_command(command: str) -> tuple:
    """
    Route a slash command to the appropriate handler function.

    This function maps slash commands to their corresponding handler functions.
    Each handler is a pure function that takes user_id and optional arguments,
    and returns a text response.

    Args:
        command: The slash command string (e.g., "/start", "/scores lab-04")

    Returns:
        Tuple of (handler_function, kwargs_dict) for the command
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
        # Parse lab argument from "/scores lab-04"
        parts = command.split(maxsplit=1)
        lab = parts[1] if len(parts) > 1 else None
        return handle_scores, {"user_id": 0, "lab": lab}
    else:
        return handle_unknown, {"user_id": 0, "command": command}


def run_test_mode(command: str) -> None:
    """
    Run a command in test mode and print result to stdout.

    Test mode allows testing bot commands without connecting to Telegram.
    It's useful for development and CI/CD verification.

    Args:
        command: The command to test (slash command or natural language)
    """
    import asyncio

    # Check if it's a natural language query (LLM-powered)
    if is_natural_language_query(command):
        result = asyncio.run(handle_natural_language(command, debug=True))
        print(result)
        sys.exit(0)

    # Route slash command to handler
    handler, kwargs = get_handler_for_command(command)

    if handler is None:
        print(f"Unknown command: {command}")
        sys.exit(1)

    # Execute handler and print result
    result = asyncio.run(handler(**kwargs))
    print(result)
    sys.exit(0)


def run_telegram_mode() -> None:
    """
    Run the bot in Telegram mode (connects to Telegram API).

    This mode connects to Telegram using the aiogram library and polls for
    incoming messages. It handles both slash commands and natural language
    queries via the LLM intent router.

    The bot uses long polling to receive updates from Telegram.
    """
    import asyncio
    from aiogram import Bot, Dispatcher, types
    from aiogram.filters import CommandStart, Command
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from handlers import KEYBOARD_BUTTONS

    config = load_config()

    # Validate BOT_TOKEN is configured
    if not config["BOT_TOKEN"]:
        print("Error: BOT_TOKEN not set. Create .env.bot.secret with your bot token.")
        sys.exit(1)

    # Initialize aiogram bot and dispatcher
    bot = Bot(token=config["BOT_TOKEN"])
    dp = Dispatcher()

    def get_keyboard_markup():
        """Build inline keyboard markup from KEYBOARD_BUTTONS configuration."""
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

    # Slash command handlers
    @dp.message(CommandStart())
    async def cmd_start(message: types.Message):
        """Handle /start command with inline keyboard."""
        result = await handle_start(message.from_user.id)
        await message.answer(result, reply_markup=get_keyboard_markup())

    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        """Handle /help command."""
        result = await handle_help(message.from_user.id)
        await message.answer(result)

    @dp.message(Command("health"))
    async def cmd_health(message: types.Message):
        """Handle /health command."""
        result = await handle_health(message.from_user.id)
        await message.answer(result)

    @dp.message(Command("labs"))
    async def cmd_labs(message: types.Message):
        """Handle /labs command."""
        result = await handle_labs(message.from_user.id)
        await message.answer(result)

    @dp.message(Command("scores"))
    async def cmd_scores(message: types.Message):
        """Handle /scores command with optional lab argument."""
        lab = (
            message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
        )
        result = await handle_scores(message.from_user.id, lab)
        await message.answer(result)

    # Natural language message handler (LLM-powered)
    @dp.message()
    async def handle_message(message: types.Message):
        """Handle natural language queries via LLM intent router."""
        result = await handle_natural_language(message.text)
        await message.answer(result)

    # Inline keyboard callback handler
    @dp.callback_query()
    async def handle_callback(callback: types.CallbackQuery):
        """Handle callback queries from inline keyboard buttons."""
        data = callback.data
        result = ""
        if data == "labs":
            result = await handle_labs(0)
        elif data == "health":
            result = await handle_health(0)
        elif data == "scores_lab-4":
            result = await handle_scores(0, "lab-4")
        elif data == "top_learners":
            result = await handle_natural_language(
                "Who are the top 5 students in lab 4?"
            )
        elif data == "help":
            result = await handle_help(0)
        else:
            result = "Unknown action"
        await callback.message.answer(result)
        await callback.answer()

    print(f"Bot started. Polling...")
    asyncio.run(dp.start_polling(bot))


def main() -> None:
    """Main entry point - parse arguments and run appropriate mode."""
    parser = argparse.ArgumentParser(description="LMS Telegram Bot")
    parser.add_argument(
        "--test",
        type=str,
        metavar="COMMAND",
        help="Test mode: run a command and print result (e.g., '/start' or 'what labs are available')",
    )

    args = parser.parse_args()

    if args.test:
        run_test_mode(args.test)
    else:
        run_telegram_mode()


if __name__ == "__main__":
    main()
