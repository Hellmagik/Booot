import asyncio
import logging
import random
import string
from typing import Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import get_settings


router = Router()
drafts: dict[int, dict[str, Any]] = {}


def action_keyboard() -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Связь с администратором", callback_data="action:admin_contact")
    keyboard.adjust(1)
    return keyboard


def request_keyboard() -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Отправить", callback_data="request:send")
    keyboard.button(text="Изменить", callback_data="request:edit")
    keyboard.button(text="Отменить", callback_data="request:cancel")
    keyboard.adjust(3)
    return keyboard


def create_ticket_id(length: int = 5) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.SystemRandom().choice(alphabet) for _ in range(length))


def request_panel_text(ticket_id: str, question_text: str | None) -> str:
    question = question_text if question_text else "— пока не заполнен"
    return (
        "<b>Связь с администратором</b>\n"
        f"Номер заявки: <code>{ticket_id}</code>\n\n"
        "1. Нажмите «Изменить».\n"
        "2. Отправьте ваш вопрос следующим сообщением.\n"
        "3. Нажмите «Отправить».\n\n"
        f"<b>Текущий вопрос:</b> {question}"
    )


async def show_main_menu(chat_id: int, bot: Bot) -> None:
    await bot.send_message(
        chat_id,
        "Выберите действие:",
        reply_markup=action_keyboard().as_markup(),
    )


async def upsert_request_panel(chat_id: int, user_id: int, bot: Bot) -> None:
    draft = drafts[user_id]
    panel_text = request_panel_text(draft["ticket_id"], draft.get("question_text"))
    panel_message_id = draft.get("panel_message_id")

    if panel_message_id is not None:
        try:
            await bot.edit_message_text(
                text=panel_text,
                chat_id=chat_id,
                message_id=panel_message_id,
                reply_markup=request_keyboard().as_markup(),
            )
            return
        except TelegramBadRequest:
            pass

    panel_message = await bot.send_message(
        chat_id,
        panel_text,
        reply_markup=request_keyboard().as_markup(),
    )
    draft["panel_message_id"] = panel_message.message_id


async def safe_delete_message(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        pass


@router.message(CommandStart())
async def start(message: Message, bot: Bot) -> None:
    drafts.pop(message.from_user.id, None)
    await safe_delete_message(bot, message.chat.id, message.message_id)
    await show_main_menu(message.chat.id, bot)


@router.message(F.text)
async def handle_text(message: Message, bot: Bot) -> None:
    user_id = message.from_user.id
    draft = drafts.get(user_id)

    await safe_delete_message(bot, message.chat.id, message.message_id)

    if draft is None:
        await show_main_menu(message.chat.id, bot)
        return

    draft["question_text"] = message.text.strip()
    await upsert_request_panel(message.chat.id, user_id, bot)


@router.callback_query(F.data == "action:admin_contact")
async def admin_contact_action(callback: CallbackQuery, bot: Bot) -> None:
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    drafts[user_id] = {
        "ticket_id": create_ticket_id(),
        "question_text": None,
        "panel_message_id": callback.message.message_id,
    }
    await callback.answer()
    await upsert_request_panel(chat_id, user_id, bot)


@router.callback_query(F.data == "request:edit")
async def request_edit_action(callback: CallbackQuery, bot: Bot) -> None:
    user_id = callback.from_user.id
    draft = drafts.get(user_id)

    if draft is None:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    await callback.answer("Отправьте новый текст вопроса")
    await upsert_request_panel(callback.message.chat.id, user_id, bot)


@router.callback_query(F.data == "request:send")
async def request_send_action(callback: CallbackQuery, bot: Bot) -> None:
    user_id = callback.from_user.id
    draft = drafts.get(user_id)

    if draft is None:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if not draft.get("question_text"):
        await callback.answer("Сначала напишите вопрос через «Изменить»", show_alert=True)
        return

    await callback.answer(f"Заявка {draft['ticket_id']} отправлена")
    if callback.message is not None:
        await safe_delete_message(bot, callback.message.chat.id, callback.message.message_id)
        await show_main_menu(callback.message.chat.id, bot)
    drafts.pop(user_id, None)


@router.callback_query(F.data == "request:cancel")
async def request_cancel_action(callback: CallbackQuery, bot: Bot) -> None:
    user_id = callback.from_user.id
    drafts.pop(user_id, None)

    await callback.answer("Заявка отменена")
    if callback.message is not None:
        await safe_delete_message(bot, callback.message.chat.id, callback.message.message_id)
        await show_main_menu(callback.message.chat.id, bot)


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
