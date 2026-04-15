import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import get_settings


router = Router()


def action_keyboard() -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Связь с администратором", callback_data="action:admin_contact")
    keyboard.adjust(1)
    return keyboard


async def safe_delete_message(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        pass


@router.message(CommandStart())
async def start(message: Message, bot: Bot) -> None:
    await safe_delete_message(bot, message.chat.id, message.message_id)
    await message.answer(
        "Выберите действие:",
        reply_markup=action_keyboard().as_markup(),
    )


@router.message(F.text)
async def handle_text(message: Message, bot: Bot) -> None:
    await safe_delete_message(bot, message.chat.id, message.message_id)
    await message.answer(
        "Выберите действие:",
        reply_markup=action_keyboard().as_markup(),
    )


@router.callback_query(F.data == "action:admin_contact")
async def admin_contact_action(callback: CallbackQuery, bot: Bot) -> None:
    await callback.answer("Администратор скоро свяжется с вами")
    if callback.message is not None:
        await safe_delete_message(bot, callback.message.chat.id, callback.message.message_id)


async def main() -> None:
    settings = get_settings()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
