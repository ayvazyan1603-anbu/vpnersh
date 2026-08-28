import html
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import config
import database.db as db
from states.user_states import TicketStates
from keyboards.user_kb import support_keyboard, cancel_state_keyboard, back_keyboard

logger = logging.getLogger(__name__)
router = Router()


def get_support_text() -> str:
    return (
        "🛟 <b>Поддержка</b>\n\n"
        "Это центр тикетов: создавайте обращения, просматривайте ответы и историю.\n\n"
        "• 🎫 Создать тикет — опишите проблему или вопрос\n"
        "• 📋 Мои тикеты — статус и переписка\n"
        "• 💬 Связаться — написать напрямую (если нужно)\n\n"
        "Старайтесь использовать тикеты — так мы быстрее поможем и ничего не потеряется."
    )


@router.callback_query(F.data == "menu_support")
async def cb_support(call: CallbackQuery):
    """Главный экран поддержки"""
    await call.message.edit_text(text=get_support_text(), reply_markup=support_keyboard())
    await call.answer()


@router.callback_query(F.data == "ticket_create")
async def cb_ticket_create(call: CallbackQuery, state: FSMContext):
    """Запрос текста тикета"""
    await state.set_state(TicketStates.waiting_text)
    text = (
        "🎫 <b>Создание тикета</b>\n\n"
        "Опишите вашу проблему или задайте вопрос подробным сообщением ниже:"
    )
    await call.message.edit_text(text=text, reply_markup=cancel_state_keyboard(back_target="menu_support"))
    await call.answer()


@router.message(TicketStates.waiting_text)
async def process_ticket_text(message: Message, state: FSMContext, bot: Bot):
    """Обработка созданного тикета"""
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or "Пользователь"
    ticket_text = message.text

    ticket_id = await db.create_ticket(user_id, username, full_name, ticket_text)
    await state.clear()

    # Уведомляем администраторов
    for admin_id in config.ADMIN_IDS:
        try:
            uname_str = f"@{username}" if username else "без username"
            await bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🚨 <b>Новый тикет в поддержку #{ticket_id}!</b>\n\n"
                    f"👤 От: {html.escape(full_name)} ({uname_str}) [ID: <code>{user_id}</code>]\n"
                    f"📝 <b>Вопрос:</b>\n{html.escape(ticket_text)}\n\n"
                    f"<i>Для ответа перейдите в /admin</i>"
                )
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")

    await message.answer(
        text=(
            f"✅ <b>Тикет #{ticket_id} успешно создан!</b>\n\n"
            f"Наш специалист ответит вам в ближайшее время. Ответ придет в этот чат."
        ),
        reply_markup=back_keyboard(back_target="menu_support")
    )


@router.callback_query(F.data == "ticket_list")
async def cb_ticket_list(call: CallbackQuery):
    """Просмотр тикетов пользователя"""
    tickets = await db.get_user_tickets(call.from_user.id)
    if not tickets:
        text = "📋 <b>Мои тикеты:</b>\n\nУ вас пока нет созданных обращений."
    else:
        text = f"📋 <b>Ваши обращения ({len(tickets)}):</b>\n\n"
        for t in tickets:
            status_emoji = "⏳ В обработке" if t["status"] == "open" else "✅ Ответ дан"
            text += (
                f"<b>Тикет #{t['id']}</b> ({status_emoji})\n"
                f"📅 {t['created_at'][:16]}\n"
                f"❓ <b>Вопрос:</b> {html.escape(t['text'][:100])}\n"
            )
            if t["admin_reply"]:
                text += f"💬 <b>Ответ поддержки:</b> {html.escape(t['admin_reply'])}\n"
            text += "────────────────────\n"

    await call.message.edit_text(text=text, reply_markup=back_keyboard(back_target="menu_support"))
    await call.answer()
