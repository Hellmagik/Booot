from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import get_settings
from handlers.admin_support import clear_user_draft
from handlers.admin_support import handle_admin_or_draft_text
from handlers.admin_support import safe_delete_message
from handlers.admin_support import show_main_menu
from services import AIService


router = Router()
settings = get_settings()
ai_service = AIService(settings=settings)


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    clear_user_draft(message.from_user.id)
    await safe_delete_message(message)
    await message.answer(
        "Привет! Я Telegram-бот с AI и поддержкой администратора.\n"
        "• Напиши сообщение — отвечу через GigaChat\n"
        "• Или нажми «Связь с администратором»"
    )
    await show_main_menu(message)


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(
        "Доступно сейчас:\n"
        "• /start — запуск\n"
        "• /help — помощь\n"
        "• Любой текст — ответ через GigaChat\n"
        "• Кнопка «Связь с администратором» — заявка админу"
    )


@router.message(F.text)
async def text_handler(message: Message) -> None:
    if await handle_admin_or_draft_text(message):
        return

    reply = await ai_service.generate_reply((message.text or "").strip())
    await message.answer(reply)
