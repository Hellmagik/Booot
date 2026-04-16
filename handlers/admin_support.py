import random
import string
import logging
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import get_settings


router = Router()
settings = get_settings()
logger = logging.getLogger(__name__)

drafts: dict[int, dict[str, Any]] = {}
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
        "1️⃣ Нажмите <b>«Изменить»</b>\n"
        "2️⃣ Отправьте ваш <b>вопрос</b>\n"
        "3️⃣ Нажмите <b>«Отправить»</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>💬 Ваш вопрос:</b>\n{question_display}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def clear_user_draft(user_id: int) -> None:
    drafts.pop(user_id, None)


async def safe_delete_message(message: Message) -> None:
    try:
        await message.delete()
    except (TelegramBadRequest, TelegramForbiddenError):
        pass


async def show_main_menu(message: Message) -> None:
    await message.answer(
        "Выберите действие или просто отправьте сообщение для AI:",
        reply_markup=action_keyboard().as_markup(),
    )


async def upsert_request_panel(callback_or_message: CallbackQuery | Message, user_id: int) -> None:
    if isinstance(callback_or_message, CallbackQuery):
        source_message = callback_or_message.message
    else:
        source_message = callback_or_message

    if source_message is None:
        return

    draft = drafts[user_id]
    panel_text = request_panel_text(draft["ticket_id"], draft.get("question_text"))
    panel_message_id = draft.get("panel_message_id")

    if panel_message_id is not None:
        try:
            await source_message.bot.edit_message_text(
                text=panel_text,
                chat_id=source_message.chat.id,
                message_id=panel_message_id,
                reply_markup=request_keyboard().as_markup(),
            )
            return
        except TelegramBadRequest:
            pass

    panel_message = await source_message.answer(
        panel_text,
        reply_markup=request_keyboard().as_markup(),
    )
    draft["panel_message_id"] = panel_message.message_id


async def handle_admin_or_draft_text(message: Message) -> bool:
    user_id = message.from_user.id
    text = (message.text or "").strip()

    if user_id in admin_reply_mode:
        if settings.admin_chat_id is None or user_id != settings.admin_chat_id:
            admin_reply_mode.pop(user_id, None)
            await message.answer("Режим ответа администратора недоступен")
            return True

        ticket_id = admin_reply_mode.pop(user_id)
        request_info = admin_requests.get(ticket_id)

        if request_info is None:
            await message.answer("Заявка не найдена")
            return True

        user_to_reply = request_info["user_id"]

        await message.bot.send_message(
            user_to_reply,
            (
                "<b>✅ Ответ администратора</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🎟 <b>По заявке:</b> <code>{ticket_id}</code>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{text}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
        )

        admin_message_id = request_info.get("admin_message_id")
        if settings.admin_chat_id is not None and admin_message_id is not None:
            try:
                await message.bot.edit_message_text(
                    chat_id=settings.admin_chat_id,
                    message_id=admin_message_id,
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

        await message.answer(
            "<b>✅ Ответ успешно отправлен пользователю</b>\n\n"
            f"🎟 Заявка: <code>{ticket_id}</code>"
        )
        admin_requests.pop(ticket_id, None)
        return True

    draft = drafts.get(user_id)
    if draft is not None:
        draft["question_text"] = text
        await upsert_request_panel(message, user_id)
        await safe_delete_message(message)
        return True

    return False


@router.callback_query(F.data == "action:admin_contact")
async def admin_contact_action(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    source_message = callback.message

    if source_message is None:
        await callback.answer("Сообщение не найдено", show_alert=True)
        return

    drafts[user_id] = {
        "ticket_id": create_ticket_id(),
        "question_text": None,
        "panel_message_id": source_message.message_id,
    }
    await callback.answer()
    await upsert_request_panel(callback, user_id)


@router.callback_query(F.data == "request:edit")
async def request_edit_action(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    if user_id not in drafts:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    await callback.answer("Отправьте новый текст вопроса")


@router.callback_query(F.data == "request:send")
async def request_send_action(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    draft = drafts.get(user_id)

    if draft is None:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if not draft.get("question_text"):
        await callback.answer("Сначала напишите вопрос через «Изменить»", show_alert=True)
        return

    if settings.admin_chat_id is None:
        await callback.answer("ADMIN_CHAT_ID не настроен в .env", show_alert=True)
        return

    user = callback.from_user
    user_name = user.full_name
    username = f"@{user.username}" if user.username else "—"

    try:
        admin_msg = await callback.bot.send_message(
            settings.admin_chat_id,
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
    except TelegramBadRequest as error:
        logger.warning("Не удалось отправить заявку в admin_chat_id=%s: %s", settings.admin_chat_id, error)
        await callback.answer("Не удалось отправить заявку администратору", show_alert=True)
        await callback.message.answer(
            "Пока не получилось отправить заявку администратору. "
            "Проверьте ADMIN_CHAT_ID и убедитесь, что администратор уже написал боту /start."
        )
        return

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
        try:
            await callback.message.delete()
        except (TelegramBadRequest, TelegramForbiddenError):
            pass
        await show_main_menu(callback.message)
    drafts.pop(user_id, None)


@router.callback_query(F.data == "request:cancel")
async def request_cancel_action(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    drafts.pop(user_id, None)

    await callback.answer("Заявка отменена")
    if callback.message is not None:
        try:
            await callback.message.delete()
        except (TelegramBadRequest, TelegramForbiddenError):
            pass
        await show_main_menu(callback.message)


@router.callback_query(F.data.startswith("admin:reply:"))
async def admin_reply_action(callback: CallbackQuery) -> None:
    ticket_id = callback.data.split(":", 2)[-1]
    admin_id = callback.from_user.id

    if settings.admin_chat_id is None or admin_id != settings.admin_chat_id:
        await callback.answer("Только для администратора", show_alert=True)
        return

    if ticket_id not in admin_requests:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    admin_reply_mode[admin_id] = ticket_id
    await callback.answer("Напишите ответ для пользователя")
