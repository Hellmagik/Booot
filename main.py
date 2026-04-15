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
admin_chat_id: int | None = None
admin_requests: dict[str, dict[str, Any]] = {}
admin_reply_mode: dict[int, str] = {}


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


def admin_ticket_keyboard(ticket_id: str) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Ответить", callback_data=f"admin:reply:{ticket_id}")
    keyboard.adjust(1)
    return keyboard


def create_ticket_id(length: int = 5) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.SystemRandom().choice(alphabet) for _ in range(length))


def request_panel_text(ticket_id: str, question_text: str | None) -> str:
    status = "✅ Заполнен" if question_text else "⏳ Ожидание"
    question_display = f"<i>{question_text}</i>" if question_text else "<i>— пока не указан</i>"
    return (
        "<b>📞 Связь с администратором</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎟 <b>Номер заявки:</b> <code>{ticket_id}</code>\n"
        f"📋 <b>Статус:</b> {status}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Инструкция:</b>\n"
        "1️⃣  Нажмите кнопку <b>«Изменить»</b>\n"
        "2️⃣  Отправьте ваш <b>вопрос</b>\n"
        "3️⃣  Нажмите <b>«Отправить»</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>💬 Ваш вопрос:</b>\n{question_display}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
    admin_id = user_id

    await safe_delete_message(bot, message.chat.id, message.message_id)

    # Check if admin is in reply mode
    if admin_id in admin_reply_mode:
        ticket_id = admin_reply_mode.pop(admin_id)
        request_info = admin_requests.get(ticket_id)

        if request_info is None:
            await bot.send_message(message.chat.id, "Заявка не найдена")
            return

        user_to_reply = request_info["user_id"]

        try:
            await bot.send_message(
                user_to_reply,
                (
                    "<b>✅ Ответ администратора</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🎟 <b>По заявке:</b> <code>{ticket_id}</code>\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{message.text}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
            )
            
            if admin_chat_id is not None and request_info.get("admin_message_id"):
                try:
                    await bot.edit_message_text(
                        chat_id=admin_chat_id,
                        message_id=request_info["admin_message_id"],
                        text=(
                            "<b>📬 Новая заявка</b>\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"🎟 <b>Номер:</b> <code>{ticket_id}</code>\n"
                            f"👤 <b>Пользователь:</b> {request_info['user_name']}\n"
                            f"🔗 <b>Username:</b> {request_info['username']}\n"
                            f"🆔 <b>User ID:</b> <code>{user_to_reply}</code>\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"💬 <b>Вопрос:</b>\n<i>{request_info['question_text']}</i>\n\n"
                            "✅ <b>Статус:</b> Ответ отправлен"
                        ),
                        reply_markup=None,
                    )
                except TelegramBadRequest:
                    pass
            
            await bot.send_message(
                message.chat.id,
                "<b>✅ Ответ успешно отправлен пользователю</b>\n\n"
                f"🎟 Заявка: <code>{ticket_id}</code>\n"
                f"📤 Отправлено пользователю: {request_info['user_name']}"
            )
            admin_requests.pop(ticket_id, None)
        except TelegramBadRequest as error:
            if "Forbidden" in str(error):
                await bot.send_message(message.chat.id, 
                    "❌ Не удалось отправить ответ\n\n"
                    "Пользователь заблокировал бота или удалил чат."
                )
            else:
                raise
        return

    # Regular user mode: filling out request
    draft = drafts.get(user_id)

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

    if admin_chat_id is not None:
        user = callback.from_user
        user_name = user.full_name
        username = f"@{user.username}" if user.username else "—"
        
        admin_msg = await bot.send_message(
            admin_chat_id,
            (
                "<b>📬 Новая заявка</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🎟 <b>Номер:</b> <code>{draft['ticket_id']}</code>\n"
                f"👤 <b>Пользователь:</b> {user_name}\n"
                f"🔗 <b>Username:</b> {username}\n"
                f"🆔 <b>User ID:</b> <code>{user.id}</code>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💬 <b>Вопрос:</b>\n<i>{draft['question_text']}</i>\n\n"
                "⏳ <b>Статус:</b> Ожидает ответа"
            ),
            reply_markup=admin_ticket_keyboard(draft["ticket_id"]).as_markup(),
        )
        admin_requests[draft["ticket_id"]] = {
            "user_id": user.id,
            "ticket_id": draft["ticket_id"],
            "question_text": draft["question_text"],
            "user_name": user_name,
            "username": username,
            "admin_message_id": admin_msg.message_id,
        }

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


@router.callback_query(F.data.startswith("admin:reply:"))
async def admin_reply_action(callback: CallbackQuery, bot: Bot) -> None:
    ticket_id = callback.data.split(":", 2)[-1]
    admin_id = callback.from_user.id

    if ticket_id not in admin_requests:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    admin_reply_mode[admin_id] = ticket_id
    await callback.answer("Напишите ответ для пользователя")





async def main() -> None:
    global admin_chat_id
    settings = get_settings()
    admin_chat_id = settings.admin_id

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
