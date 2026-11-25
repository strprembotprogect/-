import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0")
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else 0

MARKET_USERNAME = "MarketaApp"

START_TEXT = (
    "Hello, this is a <b>MarketApp Contracts</b> bot.\n\n"
    "This bot is designed to reconstruct old contracts and convert them into "
    "new smart contracts on the <b>TON</b> blockchain.\n\n"
    "Use <code>/menu</code> or the buttons below to access additional functions, "
    "request a counter agent, or open the marketplace."
)

MENU_TEXT = (
    "<b>MarketApp Contracts — Menu</b>\n\n"
    "Choose an action in the buttons below:\n"
    "• <b>Counter agent</b> — notify an agent (wait time up to <b>15 minutes</b>)\n"
    "• <b>Go to the market</b> — open <b>MarketApp</b> (<code>@MarketaApp</code>)"
)

COUNTER_AGENT_TEXT = (
    "<b>Counter agent requested</b>\n\n"
    "Your request has been sent. Please wait for an agent's response — "
    "estimated wait time is up to <b>15 minutes</b>. We will get back to you shortly."
)

MARKET_TEXT = (
    "<b>MarketApp</b>\n\n"
    "Go to the marketplace using the link below:\n"
    f"👉 @{MARKET_USERNAME}"
)


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Menu", callback_data="open_menu")],
            [InlineKeyboardButton(text="Counter agent", callback_data="counter_agent")],
            [InlineKeyboardButton(text="Go to the market", callback_data="go_market")],
        ]
    )


def menu_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Counter agent", callback_data="counter_agent")],
            [InlineKeyboardButton(text="Go to the market", callback_data="go_market")],
        ]
    )


async def send_counter_agent(bot: Bot, user_id: int, username: str | None, full_name: str) -> None:
    await bot.send_message(chat_id=user_id, text=COUNTER_AGENT_TEXT)

    if ADMIN_ID:
        user_handle = f"@{username}" if username else "нет username"
        admin_text = (
            "🔔 <b>New counter agent request!</b>\n\n"
            f"• <b>User:</b> {user_handle}\n"
            f"• <b>Name:</b> {full_name}\n"
            f"• <b>ID:</b> <code>{user_id}</code>"
        )
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=admin_text)
        except Exception as exc:
            logging.warning("Не удалось отправить уведомление админу: %s", exc)


async def send_market_info(bot: Bot, user_id: int) -> None:
    await bot.send_message(chat_id=user_id, text=MARKET_TEXT)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN:
        raise ValueError("Не задан BOT_TOKEN в переменных окружения Railway.")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        await message.answer(START_TEXT, reply_markup=start_keyboard())

    @dp.message(Command("menu"))
    async def cmd_menu(message: Message) -> None:
        await message.answer(MENU_TEXT, reply_markup=menu_actions_keyboard())

    @dp.callback_query(F.data == "open_menu")
    async def cb_open_menu(callback: CallbackQuery) -> None:
        if callback.message:
            await callback.message.answer(MENU_TEXT, reply_markup=menu_actions_keyboard())
        await callback.answer()

    @dp.callback_query(F.data == "counter_agent")
    async def cb_counter_agent(callback: CallbackQuery) -> None:
        user = callback.from_user
        await send_counter_agent(
            bot=bot,
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
        )
        await callback.answer("Request sent")

    @dp.callback_query(F.data == "go_market")
    async def cb_go_market(callback: CallbackQuery) -> None:
        await send_market_info(bot=bot, user_id=callback.from_user.id)
        await callback.answer()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
