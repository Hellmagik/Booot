from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import get_settings
from services import AIService


router = Router()
settings = get_settings()
ai_service = AIService(settings=settings)


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "Привет! Я Telegram-бот с AI.\n"
        "Отправь сообщение, и я отвечу.\n"
        "Команда /help — подсказка."
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(
        "Доступно сейчас:\n"
        "• /start — запуск\n"
        "• /help — помощь\n"
        "• Любой текст — ответ через GigaChat"
    )


@router.message(F.text)
async def text_handler(message: Message) -> None:
    reply = await ai_service.generate_reply(message.text or "")
    await message.answer(reply)
