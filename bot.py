import asyncio
import logging
import os
import time

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
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

MARKET_USERNAME = "MarketApp"
COUNTER_AGENT_COOLDOWN_SEC = 180  # 3 минуты между вызовами от одного пользователя

last_counter_agent_call: dict[int, float] = {}

START_TEXT = (
    "Hello, this is a <b>MarketApp Contracts</b> bot.\n\n"
    "This bot is designed to reconstruct old contracts and convert them into "
    "new smart contracts on the <b>TON</b> blockchain.\n\n"
    "Use <code>/menu</code> or the buttons below to access additional functions, "
    "read instructions, request a counter agent, or open the marketplace."
)

MENU_TEXT = (
    "<b>MarketApp Contracts — Menu</b>\n"
    "<i>TON smart contract reconstruction • Counter agent response up to 15 min</i>\n\n"
    "Choose an action below:\n"
    "• <b>Instructions</b> — what to prepare before reconstructing a contract\n"
    "• <b>Counter agent</b> — notify an agent (wait time up to <b>15 minutes</b>)\n"
    f"• <b>Go to the market</b> — open <b>MarketApp</b> (<code>@{MARKET_USERNAME}</code>)"
)

INSTRUCTIONS_TEXT = (
    "<b>MarketApp Contracts — Instructions</b>\n\n"
    "Before requesting a counter agent, prepare a brief summary of your task:\n"
    "• <b>Old contract:</b> link, address, or text of the current contract you want to reconstruct.\n"
    "• <b>Goal in TON:</b> what smart contract logic or behavior you need on the <b>TON</b> blockchain.\n"
    "• <b>Details:</b> any deadlines, key parameters, or special requirements.\n\n"
    f"Click <b>Counter agent</b> when you are ready — an agent will respond within <b>15 minutes</b>, "
    f"or open <b>MarketApp</b> (<code>@{MARKET_USERNAME}</code>)."
)

COUNTER_AGENT_TEXT = (
    "<b>Counter agent requested</b>\n\n"
    "Your request has been sent. Please wait for an agent's response — "
    "estimated wait time is up to <b>15 minutes</b>. We will get back to you shortly.\n\n"
    "If you haven't prepared your details yet, open <b>Instructions</b> below."
)

MARKET_TEXT = (
    "<b>MarketApp</b>\n\n"
    "Go to the marketplace using the link or button below:\n"
    f"👉 @{MARKET_USERNAME}"
)


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Menu", callback_data="open_menu")],
            [InlineKeyboardButton(text="📖 Instructions", callback_data="instructions")],
            [InlineKeyboardButton(text="🙋 Counter agent", callback_data="counter_agent")],
            [InlineKeyboardButton(text="🛒 Go to the market", callback_data="go_market")],
        ]
    )


def menu_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📖 Instructions", callback_data="instructions")],
            [InlineKeyboardButton(text="🙋 Counter agent", callback_data="counter_agent")],
            [InlineKeyboardButton(text="🛒 Go to the market", callback_data="go_market")],
        ]
    )


def counter_agent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📖 Instructions", callback_data="instructions")],
            [InlineKeyboardButton(text="🛒 Go to the market", callback_data="go_market")],
            [InlineKeyboardButton(text="⬅️ Back to menu", callback_data="open_menu")],
        ]
    )


def back_to_menu_keyboard(include_market_url: bool = False) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if include_market_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🔗 Open @{MARKET_USERNAME}",
                    url=f"https://t.me/{MARKET_USERNAME}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Back to menu", callback_data="open_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_menu(bot: Bot, chat_id: int) -> None:
    await bot.send_message(
        chat_id=chat_id,
        text=MENU_TEXT,
        reply_markup=menu_actions_keyboard(),
    )


async def send_instructions(bot: Bot, chat_id: int) -> None:
    await bot.send_message(
        chat_id=chat_id,
        text=INSTRUCTIONS_TEXT,
        reply_markup=back_to_menu_keyboard(include_market_url=False),
    )


async def send_counter_agent(
    bot: Bot,
    user_id: int,
    username: str | None,
    full_name: str,
) -> tuple[bool, int]:
    now = time.monotonic()
    last_call = last_counter_agent_call.get(user_id, 0.0)
    elapsed = now - last_call

    if last_call > 0 and elapsed < COUNTER_AGENT_COOLDOWN_SEC:
        remaining = int(COUNTER_AGENT_COOLDOWN_SEC - elapsed) + 1
        return False, remaining

    last_counter_agent_call[user_id] = now

    await bot.send_message(
        chat_id=user_id,
        text=COUNTER_AGENT_TEXT,
        reply_markup=counter_agent_keyboard(),
    )

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

    return True, 0


async def send_market_info(bot: Bot, chat_id: int) -> None:
    await bot.send_message(
        chat_id=chat_id,
        text=MARKET_TEXT,
        reply_markup=back_to_menu_keyboard(include_market_url=True),
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN:
        raise ValueError("Не задан BOT_TOKEN в переменных окружения Railway.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        await message.answer(START_TEXT, reply_markup=start_keyboard())

    @dp.message(Command("menu"))
    async def cmd_menu(message: Message) -> None:
        await send_menu(bot=bot, chat_id=message.chat.id)

    @dp.callback_query(F.data == "open_menu")
    async def cb_open_menu(callback: CallbackQuery) -> None:
        if callback.message:
            await send_menu(bot=bot, chat_id=callback.message.chat.id)
        await callback.answer()

    @dp.callback_query(F.data == "instructions")
    async def cb_instructions(callback: CallbackQuery) -> None:
        if callback.message:
            await send_instructions(bot=bot, chat_id=callback.message.chat.id)
        await callback.answer()

    @dp.callback_query(F.data == "counter_agent")
    async def cb_counter_agent(callback: CallbackQuery) -> None:
        user = callback.from_user
        sent, remaining = await send_counter_agent(
            bot=bot,
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
        )
        if sent:
            await callback.answer("Request sent")
        else:
            await callback.answer(
                f"Please wait {remaining}s before sending another request",
                show_alert=False,
            )

    @dp.callback_query(F.data == "go_market")
    async def cb_go_market(callback: CallbackQuery) -> None:
        if callback.message:
            await send_market_info(bot=bot, chat_id=callback.message.chat.id)
        await callback.answer()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
