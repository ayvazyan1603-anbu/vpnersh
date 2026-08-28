import html
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

import config
import database.db as db
from states.admin_states import AdminStates
from keyboards.admin_kb import (
    admin_main_keyboard,
    admin_prices_keyboard,
    admin_tickets_list_keyboard,
    admin_ticket_actions_keyboard,
    admin_admins_keyboard,
    admin_back_keyboard
)

logger = logging.getLogger(__name__)
router = Router()

PLAN_TITLES = {
    "price_1_month": "1 месяц",
    "price_3_months": "3 месяца",
    "price_6_months": "6 месяцев",
    "price_12_months": "12 месяцев / 1 год",
}


# ── /admin ВХОД ПО АЙДИ ────────────────────────────────────────────────────────
@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Вход в панель администратора (автоматически по Telegram ID)"""
    await state.clear()
    user_id = message.from_user.id

    if await db.is_admin_user(user_id):
        await message.answer(
            f"🛠 <b>Панель управления администратора</b>\n\n"
            f"👤 Вы авторизованы как администратор (ID: <code>{user_id}</code>)",
            reply_markup=admin_main_keyboard()
        )
    else:
        # Если ID нет в списке, даем возможность ввести мастер-пароль
        await state.set_state(AdminStates.waiting_password)
        await message.answer(
            "🔐 <b>Доступ ограничен.</b>\n\n"
            f"Ваш ID (<code>{user_id}</code>) не найден в списке администраторов.\n"
            "Если у вас есть мастер-пароль, введите его ниже:"
        )


@router.message(AdminStates.waiting_password)
async def process_admin_password(message: Message, state: FSMContext):
    """Авторизация по паролю и автоматическое добавление ID в базу админов"""
    await message.delete()
    user_id = message.from_user.id

    if message.text.strip() == config.ADMIN_PASSWORD:
        await db.add_admin_id(user_id)
        await state.clear()
        await message.answer(
            f"✅ <b>Авторизация успешна!</b>\n\n"
            f"Ваш ID (<code>{user_id}</code>) добавлен в список постоянных администраторов.",
            reply_markup=admin_main_keyboard()
        )
    else:
        await state.clear()
        await message.answer("❌ <b>Неверный пароль.</b>")


@router.callback_query(F.data == "admin_menu")
async def cb_admin_menu(call: CallbackQuery, state: FSMContext):
    """Главное меню админ-панели"""
    await state.clear()
    if not await db.is_admin_user(call.from_user.id):
        await call.answer("Доступ запрещен", show_alert=True)
        return

    await call.message.edit_text(
        "🛠 <b>Панель управления администратора</b>\n\nВыберите нужный раздел:",
        reply_markup=admin_main_keyboard()
    )
    await call.answer()


# ── УПРАВЛЕНИЕ ЦЕНАМИ ────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_prices")
async def cb_admin_prices(call: CallbackQuery, state: FSMContext):
    """Меню управления ценами тарифов"""
    await state.clear()
    if not await db.is_admin_user(call.from_user.id):
        return

    prices = await db.get_prices()
    text = (
        "💰 <b>Управление ценами тарифов</b>\n\n"
        "Нажмите на тариф ниже, чтобы изменить его стоимость в рублях:\n\n"
        f"• 1 месяц: <b>{prices['price_1_month']} ₽</b>\n"
        f"• 3 месяца: <b>{prices['price_3_months']} ₽</b>\n"
        f"• 6 месяцев: <b>{prices['price_6_months']} ₽</b>\n"
        f"• 12 месяцев: <b>{prices['price_12_months']} ₽</b>"
    )
    await call.message.edit_text(text=text, reply_markup=admin_prices_keyboard(prices))
    await call.answer()


@router.callback_query(F.data.startswith("admin_set_price:"))
async def cb_start_set_price(call: CallbackQuery, state: FSMContext):
    """Запрос новой цены для выбранного тарифа"""
    if not await db.is_admin_user(call.from_user.id):
        return

    plan_key = call.data.split("admin_set_price:")[1]
    title = PLAN_TITLES.get(plan_key, plan_key)
    prices = await db.get_prices()
    current_price = prices.get(plan_key, 0)

    await state.set_state(AdminStates.waiting_new_price)
    await state.update_data(editing_plan_key=plan_key)

    text = (
        f"✏️ <b>Изменение цены: {title}</b>\n\n"
        f"Текущая цена: <b>{current_price} ₽</b>\n\n"
        "Введите новую стоимость в рублях (целое число):"
    )
    await call.message.edit_text(text=text, reply_markup=admin_back_keyboard(back_target="admin_prices"))
    await call.answer()


@router.message(AdminStates.waiting_new_price)
async def process_new_price(message: Message, state: FSMContext):
    """Сохранение новой цены в базу данных"""
    if not await db.is_admin_user(message.from_user.id):
        await state.clear()
        return

    text = message.text.strip()
    if not text.isdigit() or int(text) < 0:
        await message.answer("❌ Введите корректное положительное число (например, 199):")
        return

    new_price = int(text)
    data = await state.get_data()
    plan_key = data.get("editing_plan_key")
    await state.clear()

    await db.set_price(plan_key, new_price)
    title = PLAN_TITLES.get(plan_key, plan_key)

    prices = await db.get_prices()
    await message.answer(
        f"✅ <b>Цена для тарифа «{title}» успешно обновлена на {new_price} ₽!</b>\n\n"
        "Новая цена сразу применяется в меню пользователей.",
        reply_markup=admin_prices_keyboard(prices)
    )


# ── УПРАВЛЕНИЕ ТИКЕТАМИ ──────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_tickets")
async def cb_admin_open_tickets(call: CallbackQuery, state: FSMContext):
    """Список открытых тикетов техподдержки"""
    await state.clear()
    if not await db.is_admin_user(call.from_user.id):
        return

    tickets = await db.get_open_tickets()
    if not tickets:
        await call.message.edit_text(
            "🎫 <b>Управление тикетами</b>\n\n"
            "✅ <b>Все тикеты обработаны!</b>\n"
            "Новых открытых обращений от пользователей нет.",
            reply_markup=admin_tickets_list_keyboard([], show_all=False)
        )
        await call.answer()
        return

    text = (
        f"🎫 <b>Открытые тикеты ({len(tickets)}):</b>\n\n"
        "Выберите обращение для просмотра и ответа:"
    )
    await call.message.edit_text(text=text, reply_markup=admin_tickets_list_keyboard(tickets, show_all=False))
    await call.answer()


@router.callback_query(F.data == "admin_all_tickets")
async def cb_admin_all_tickets(call: CallbackQuery, state: FSMContext):
    """Список всех тикетов (включая закрытые)"""
    await state.clear()
    if not await db.is_admin_user(call.from_user.id):
        return

    tickets = await db.get_all_tickets(limit=20)
    text = (
        f"📋 <b>Все последние тикеты ({len(tickets)}):</b>\n\n"
        "⏳ — открыт, ✅ — отвечен / закрыт"
    )
    await call.message.edit_text(text=text, reply_markup=admin_tickets_list_keyboard(tickets, show_all=True))
    await call.answer()


@router.callback_query(F.data.startswith("admin_view_ticket:"))
async def cb_view_ticket(call: CallbackQuery, state: FSMContext):
    """Просмотр деталей конкретного тикета"""
    await state.clear()
    if not await db.is_admin_user(call.from_user.id):
        return

    ticket_id = int(call.data.split("admin_view_ticket:")[1])
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        await call.message.edit_text("❌ Тикет не найден.", reply_markup=admin_back_keyboard(back_target="admin_tickets"))
        await call.answer()
        return

    status_str = "⏳ Открыт (ожидает ответа)" if ticket["status"] == "open" else "✅ Ответ дан / Закрыт"
    uname_str = f"@{ticket['username']}" if ticket.get("username") else "без username"

    text = (
        f"🎫 <b>Тикет #{ticket['id']}</b> ({status_str})\n\n"
        f"👤 <b>Пользователь:</b> {html.escape(ticket['full_name'] or '')} ({uname_str})\n"
        f"🆔 <b>ID:</b> <code>{ticket['user_id']}</code>\n"
        f"📅 <b>Дата:</b> {ticket['created_at'][:16]}\n\n"
        f"📝 <b>Вопрос:</b>\n<blockquote>{html.escape(ticket['text'])}</blockquote>\n"
    )
    if ticket.get("admin_reply"):
        text += f"\n💬 <b>Предыдущий ответ:</b>\n<blockquote>{html.escape(ticket['admin_reply'])}</blockquote>"

    is_open = (ticket["status"] == "open")
    await call.message.edit_text(text=text, reply_markup=admin_ticket_actions_keyboard(ticket_id, is_open=is_open))
    await call.answer()


@router.callback_query(F.data.startswith("admin_reply_ticket:"))
async def cb_start_ticket_reply(call: CallbackQuery, state: FSMContext):
    """Запрос текста ответа на тикет"""
    if not await db.is_admin_user(call.from_user.id):
        return

    ticket_id = int(call.data.split("admin_reply_ticket:")[1])
    await state.set_state(AdminStates.waiting_ticket_reply)
    await state.update_data(reply_ticket_id=ticket_id)

    text = (
        f"✍️ <b>Ответ на тикет #{ticket_id}</b>\n\n"
        "Отправьте текст ответа сообщением ниже. Он будет доставлен пользователю в чат с ботом:"
    )
    await call.message.edit_text(text=text, reply_markup=admin_back_keyboard(back_target=f"admin_view_ticket:{ticket_id}"))
    await call.answer()


@router.message(AdminStates.waiting_ticket_reply)
async def process_ticket_reply(message: Message, state: FSMContext, bot: Bot):
    """Отправка ответа пользователю и сохранение в БД"""
    if not await db.is_admin_user(message.from_user.id):
        await state.clear()
        return

    data = await state.get_data()
    ticket_id = data.get("reply_ticket_id")
    reply_text = message.text
    await state.clear()

    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        await message.answer("❌ Тикет не найден.", reply_markup=admin_back_keyboard(back_target="admin_tickets"))
        return

    await db.reply_ticket(ticket_id, reply_text)

    # Отправляем ответ пользователю в чат
    try:
        await bot.send_message(
            chat_id=ticket["user_id"],
            text=(
                f"📩 <b>Ответ службы поддержки на ваш тикет #{ticket_id}:</b>\n\n"
                f"{html.escape(reply_text)}"
            )
        )
        delivered_info = "Сообщение успешно доставлено в Telegram."
    except Exception as e:
        delivered_info = f"Не удалось отправить в Telegram ({e}), но ответ сохранен в тикетах."

    await message.answer(
        f"✅ <b>Ответ на тикет #{ticket_id} успешно отправлен!</b>\n\n{delivered_info}",
        reply_markup=admin_back_keyboard(back_target="admin_tickets")
    )


@router.callback_query(F.data.startswith("admin_close_ticket:"))
async def cb_close_ticket(call: CallbackQuery):
    """Закрытие тикета"""
    if not await db.is_admin_user(call.from_user.id):
        return

    ticket_id = int(call.data.split("admin_close_ticket:")[1])
    await db.close_ticket(ticket_id)
    await call.answer("Тикет закрыт", show_alert=True)
    await cb_view_ticket(call, FSMContext)


# ── УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ ──────────────────────────────────────────────
@router.callback_query(F.data == "admin_list_admins")
async def cb_list_admins(call: CallbackQuery, state: FSMContext):
    """Список действующих админов"""
    await state.clear()
    if not await db.is_admin_user(call.from_user.id):
        return

    admins = await db.get_all_admins()
    text = "👥 <b>Список администраторов:</b>\n\n"
    for aid in admins:
        text += f"• ID: <code>{aid}</code>\n"

    await call.message.edit_text(text=text, reply_markup=admin_admins_keyboard())
    await call.answer()


@router.callback_query(F.data == "admin_add_admin")
async def cb_start_add_admin(call: CallbackQuery, state: FSMContext):
    """Запрос ID нового администратора"""
    if not await db.is_admin_user(call.from_user.id):
        return

    await state.set_state(AdminStates.waiting_add_admin_id)
    text = (
        "➕ <b>Добавление администратора</b>\n\n"
        "Отправьте числовой Telegram ID пользователя, которому нужно выдать права администратора:"
    )
    await call.message.edit_text(text=text, reply_markup=admin_back_keyboard(back_target="admin_list_admins"))
    await call.answer()


@router.message(AdminStates.waiting_add_admin_id)
async def process_add_admin(message: Message, state: FSMContext):
    """Добавление ID админа в базу"""
    if not await db.is_admin_user(message.from_user.id):
        await state.clear()
        return

    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ ID должен состоять только из цифр. Попробуйте еще раз:")
        return

    new_admin_id = int(text)
    await db.add_admin_id(new_admin_id)
    await state.clear()

    await message.answer(
        f"✅ Пользователь с ID <code>{new_admin_id}</code> успешно добавлен в администраторы!\n"
        "Теперь он может использовать команду /admin без пароля.",
        reply_markup=admin_back_keyboard(back_target="admin_list_admins")
    )


# ── СТАТИСТИКА ───────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(call: CallbackQuery):
    if not await db.is_admin_user(call.from_user.id):
        return

    stats = await db.get_global_stats()
    text = (
        "📊 <b>Статистика сервиса:</b>\n\n"
        f"• Всего зарегистрировано: <b>{stats['total_users']}</b> пользователей\n"
        f"• Активных подписок: <b>{stats['active_subs']}</b>\n"
        f"• Открытых тикетов: <b>{stats['open_tickets']}</b>\n"
        f"• Суммарный баланс пользователей: <b>{stats['total_balance']} ₽</b>"
    )
    await call.message.edit_text(text=text, reply_markup=admin_back_keyboard())
    await call.answer()


# ── СОЗДАНИЕ ПРОМОКОДОВ ───────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_create_promo")
async def cb_create_promo(call: CallbackQuery, state: FSMContext):
    if not await db.is_admin_user(call.from_user.id):
        return

    await state.set_state(AdminStates.waiting_promocode_data)
    text = (
        "🎁 <b>Создание промокода</b>\n\n"
        "Отправьте данные промокода в формате:\n"
        "<code>КОД ТИП ЗНАЧЕНИЕ АКТИВАЦИИ</code>\n\n"
        "Примеры:\n"
        "• <code>BONUS100 balance 100 50</code> (100 руб на баланс, 50 активаций)\n"
        "• <code>FREE7DAYS days 7 100</code> (7 дней подписки, 100 активаций)"
    )
    await call.message.edit_text(text=text, reply_markup=admin_back_keyboard())
    await call.answer()


@router.message(AdminStates.waiting_promocode_data)
async def process_create_promo(message: Message, state: FSMContext):
    if not await db.is_admin_user(message.from_user.id):
        await state.clear()
        return

    parts = message.text.strip().split()
    if len(parts) < 3:
        await message.answer("❌ Неверный формат. Пример: <code>BONUS100 balance 100 50</code>", reply_markup=admin_back_keyboard())
        return

    code = parts[0]
    reward_type = parts[1].lower()
    if reward_type not in ("balance", "days"):
        await message.answer("❌ Тип должен быть <code>balance</code> или <code>days</code>.")
        return

    try:
        reward_value = int(parts[2])
        max_activations = int(parts[3]) if len(parts) > 3 else 100
    except ValueError:
        await message.answer("❌ Значение и количество активаций должны быть числами.")
        return

    created = await db.create_promocode(code, reward_type, reward_value, max_activations)
    await state.clear()
    if created:
        await message.answer(
            f"✅ Промокод <code>{code.upper()}</code> успешно создан!\n"
            f"Тип: {reward_type}, Награда: {reward_value}, Активаций: {max_activations}",
            reply_markup=admin_back_keyboard()
        )
    else:
        await message.answer("❌ Ошибка создания промокода (возможно, такой код уже есть).", reply_markup=admin_back_keyboard())


# ── РАССЫЛКА ─────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_broadcast")
async def cb_broadcast(call: CallbackQuery, state: FSMContext):
    if not await db.is_admin_user(call.from_user.id):
        return

    await state.set_state(AdminStates.waiting_broadcast_text)
    await call.message.edit_text(
        "📢 <b>Рассылка сообщений</b>\n\nОтправьте текст сообщения для рассылки всем пользователям бота:",
        reply_markup=admin_back_keyboard()
    )
    await call.answer()


@router.message(AdminStates.waiting_broadcast_text)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not await db.is_admin_user(message.from_user.id):
        await state.clear()
        return

    broadcast_text = message.text
    await state.clear()
    await message.answer("⏳ Рассылка запущена...")

    count_success = 0
    count_failed = 0

    async with db.aiosqlite.connect(db.DB_PATH) as conn:
        cursor = await conn.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()

    for row in rows:
        uid = row[0]
        try:
            await bot.send_message(chat_id=uid, text=broadcast_text)
            count_success += 1
        except Exception:
            count_failed += 1

    await message.answer(
        f"📢 <b>Рассылка завершена!</b>\n\n"
        f"✅ Доставлено: <b>{count_success}</b>\n"
        f"❌ Ошибок: <b>{count_failed}</b>",
        reply_markup=admin_back_keyboard()
    )
