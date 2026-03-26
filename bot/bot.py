#!/usr/bin/env python3
"""
Telegram bot entry point with --test mode.

Usage:
    uv run bot.py --test "/start"           # Test mode, slash command
    uv run bot.py --test "what labs..."     # Test mode, natural language
    uv run bot.py                           # Normal mode, connects to Telegram
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
    """
    text = text.strip()
    return not text.startswith("/")


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
        return handle_unknown, {"user_id": 0, "command": command}


def run_test_mode(command: str) -> None:
    """Run a command in test mode and print result to stdout."""
    import asyncio

    # Check if it's a natural language query
    if is_natural_language_query(command):
        result = asyncio.run(handle_natural_language(command, debug=True))
        print(result)
        sys.exit(0)

    handler, kwargs = get_handler_for_command(command)

    if handler is None:
        print(f"Unknown command: {command}")
        sys.exit(1)

    result = asyncio.run(handler(**kwargs))
    print(result)
    sys.exit(0)


def run_telegram_mode() -> None:
    """Run the bot in Telegram mode (connects to Telegram API)."""
    import asyncio
    from aiogram import Bot, Dispatcher, types
    from aiogram.filters import CommandStart, Command
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from handlers import KEYBOARD_BUTTONS

    config = load_config()

    if not config["BOT_TOKEN"]:
        print("Error: BOT_TOKEN not set. Create .env.bot.secret with your bot token.")
        sys.exit(1)

    bot = Bot(token=config["BOT_TOKEN"])
    dp = Dispatcher()

    def get_keyboard_markup():
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

    @dp.message(CommandStart())
    async def cmd_start(message: types.Message):
        result = await handle_start(message.from_user.id)
        await message.answer(result, reply_markup=get_keyboard_markup())

    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        result = await handle_help(message.from_user.id)
        await message.answer(result)

    @dp.message(Command("health"))
    async def cmd_health(message: types.Message):
        result = await handle_health(message.from_user.id)
        await message.answer(result)

    @dp.message(Command("labs"))
    async def cmd_labs(message: types.Message):
        result = await handle_labs(message.from_user.id)
        await message.answer(result)

    @dp.message(Command("scores"))
    async def cmd_scores(message: types.Message):
        lab = (
            message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
        )
        result = await handle_scores(message.from_user.id, lab)
        await message.answer(result)

    @dp.message()
    async def handle_message(message: types.Message):
        # Handle natural language queries via LLM
        result = await handle_natural_language(message.text)
        await message.answer(result)

    # Handle callback queries from inline buttons
    @dp.callback_query()
    async def handle_callback(callback: types.CallbackQuery):
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
