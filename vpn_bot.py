import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Токен бота
TOKEN = os.getenv("BOT_TOKEN", "8898632185:AAEjeyDm6luvEt4jnmgQYJKCWKBCvNBBmlA")
SUPPORT_USERNAME = "tigranayvvv"

dp = Dispatcher()

# --- КЛАВИАТУРЫ ---

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    buttons = [
        [
            InlineKeyboardButton(text="💰 Баланс: 0 ₽", callback_data="menu_balance")
        ],
        [
            InlineKeyboardButton(text="🧪 Тестовая подписка", callback_data="menu_trial"),
            InlineKeyboardButton(text="💎 Купить подписку", callback_data="menu_tariffs")
        ],
        [
            InlineKeyboardButton(text="🎫 Промокод", callback_data="menu_promocode"),
            InlineKeyboardButton(text="🤝 Партнерка", callback_data="menu_partner")
        ],
        [
            InlineKeyboardButton(text="🛠 Техподдержка", callback_data="menu_support"),
            InlineKeyboardButton(text="ℹ️ Инфо", callback_data="menu_info")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_balance_keyboard() -> InlineKeyboardMarkup:
    """Меню баланса"""
    buttons = [
        [
            InlineKeyboardButton(text="📊 История операций", callback_data="sub_history"),
            InlineKeyboardButton(text="💳 Пополнить", callback_data="sub_deposit")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_tariffs_keyboard() -> InlineKeyboardMarkup:
    """Меню тарифов"""
    buttons = [
        [
            InlineKeyboardButton(text="Стандартный", callback_data="tariff_standard")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_partner_keyboard() -> InlineKeyboardMarkup:
    """Меню партнерки / реферальной программы"""
    buttons = [
        [InlineKeyboardButton(text="📝 Создать приглашение", callback_data="partner_invite")],
        [InlineKeyboardButton(text="📱 Показать QR код", callback_data="partner_qr")],
        [InlineKeyboardButton(text="👥 Список рефералов", callback_data="partner_list")],
        [InlineKeyboardButton(text="📊 Аналитика", callback_data="partner_analytics")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_support_keyboard() -> InlineKeyboardMarkup:
    """Меню техподдержки"""
    buttons = [
        [InlineKeyboardButton(text="🎫 Создать тикет", callback_data="ticket_create")],
        [InlineKeyboardButton(text="📋 Мои тикеты", callback_data="ticket_list")],
        [InlineKeyboardButton(text="💬 Связаться с поддержкой", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard(back_target: str = "main_menu") -> InlineKeyboardMarkup:
    """Универсальная кнопка назад"""
    buttons = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_target)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- ТЕКСТЫ СООБЩЕНИЙ ---

def get_main_text(user_full_name: str) -> str:
    return (
        f"👤 <b>{user_full_name}</b>\n\n"
        f"📱 Подписка: ❌ Отсутствует\n\n"
        f"Выберите действие:"
    )


def get_balance_text() -> str:
    return (
        f"💰 <b>Баланс: 0 ₽</b>\n\n"
        f"Выберите действие:"
    )


def get_tariffs_text() -> str:
    return (
        f"📦 <b>Выберите тариф</b>\n\n"
        f"<b>Стандартный — ∞ / 3 📱  от 149₽</b>\n"
        f"<i>Базовый тарифный план</i>"
    )


def get_partner_text(bot_username: str, user_id: int) -> str:
    ref_code = f"ref{user_id}"
    return (
        f"👥 <b>Реферальная программа</b>\n\n"
        f"📊 <b>Ваша статистика:</b>\n"
        f"• Приглашено пользователей: 0\n"
        f"• Сделали первое пополнение: 0\n"
        f"• Активных рефералов: 0\n"
        f"• Конверсия: 0%\n"
        f"• Заработано всего: 0 ₽\n"
        f"• За последний месяц: 0 ₽\n\n"
        f"🎁 <b>Как работают награды:</b>\n"
        f"• Вы получаете при первом пополнении реферала: 10 ₽\n"
        f"• Комиссия с каждого пополнения реферала: 0%\n\n"
        f"🤖 <b>Ссылка на бота:</b>\n"
        f"<code>https://t.me/{bot_username}?start={ref_code}</code>\n\n"
        f"🆔 <b>Ваш код:</b> <code>{ref_code}</code>\n\n"
        f"📢 <b>Приглашайте друзей и зарабатывайте!</b>"
    )


def get_support_text() -> str:
    return (
        f"🛟 <b>Поддержка</b>\n\n"
        f"Это центр тикетов: создавайте обращения, просматривайте ответы и историю.\n\n"
        f"• 🎫 Создать тикет — опишите проблему или вопрос\n"
        f"• 📋 Мои тикеты — статус и переписка\n"
        f"• 💬 Связаться — написать напрямую (если нужно)\n\n"
        f"Старайтесь использовать тикеты — так мы быстрее поможем и ничего не потеряется."
    )


# --- ХЭНДЛЕРЫ КОМАНД И НАВИГАЦИИ ---

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Стартовое сообщение с главным меню"""
    name = message.from_user.full_name or "Пользователь"
    await message.answer(
        text=get_main_text(name),
        reply_markup=get_main_keyboard()
    )


@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(call: CallbackQuery):
    """Возврат в главное меню"""
    name = call.from_user.full_name or "Пользователь"
    await call.message.edit_text(
        text=get_main_text(name),
        reply_markup=get_main_keyboard()
    )
    await call.answer()


@dp.callback_query(F.data == "menu_balance")
async def cb_balance(call: CallbackQuery):
    """Раздел: Баланс"""
    await call.message.edit_text(
        text=get_balance_text(),
        reply_markup=get_balance_keyboard()
    )
    await call.answer()


@dp.callback_query(F.data == "menu_tariffs")
async def cb_tariffs(call: CallbackQuery):
    """Раздел: Купить подписку / Тарифы"""
    await call.message.edit_text(
        text=get_tariffs_text(),
        reply_markup=get_tariffs_keyboard()
    )
    await call.answer()


@dp.callback_query(F.data == "menu_partner")
async def cb_partner(call: CallbackQuery, bot: Bot):
    """Раздел: Партнерка / Реферальная программа"""
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "bot"
    await call.message.edit_text(
        text=get_partner_text(bot_username, call.from_user.id),
        reply_markup=get_partner_keyboard(),
        disable_web_page_preview=True
    )
    await call.answer()


@dp.callback_query(F.data == "menu_support")
async def cb_support(call: CallbackQuery):
    """Раздел: Техподдержка"""
    await call.message.edit_text(
        text=get_support_text(),
        reply_markup=get_support_keyboard()
    )
    await call.answer()


@dp.callback_query(F.data == "menu_trial")
async def cb_trial(call: CallbackQuery):
    """Раздел: Тестовая подписка"""
    await call.message.edit_text(
        text="🧪 <b>Тестовая подписка</b>\n\nВы можете активировать бесплатный пробный период на 3 дня.",
        reply_markup=get_back_keyboard()
    )
    await call.answer()


@dp.callback_query(F.data == "menu_promocode")
async def cb_promocode(call: CallbackQuery):
    """Раздел: Промокод"""
    await call.message.edit_text(
        text="🎫 <b>Активация промокода</b>\n\nОтправьте промокод в чат для получения бонуса.",
        reply_markup=get_back_keyboard()
    )
    await call.answer()


@dp.callback_query(F.data == "menu_info")
async def cb_info(call: CallbackQuery):
    """Раздел: Инфо"""
    await call.message.edit_text(
        text="ℹ️ <b>Информация о сервисе</b>\n\nБыстрый и надежный VPN без ограничений скорости и рекламы.",
        reply_markup=get_back_keyboard()
    )
    await call.answer()


# --- ДОПОЛНИТЕЛЬНЫЕ КНОПКИ ПОДМЕНЮ ---

@dp.callback_query(F.data == "sub_history")
async def cb_history(call: CallbackQuery):
    await call.message.edit_text(
        text="📊 <b>История операций:</b>\n\nСписок операций пуст.",
        reply_markup=get_back_keyboard(back_target="menu_balance")
    )
    await call.answer()


@dp.callback_query(F.data == "sub_deposit")
async def cb_deposit(call: CallbackQuery):
    await call.message.edit_text(
        text="💳 <b>Пополнение баланса</b>\n\nВыберите способ оплаты для пополнения счета.",
        reply_markup=get_back_keyboard(back_target="menu_balance")
    )
    await call.answer()


@dp.callback_query(F.data == "tariff_standard")
async def cb_tariff_standard(call: CallbackQuery):
    await call.message.edit_text(
        text="📦 <b>Тариф «Стандартный»</b>\n\n• Безлимитный трафик: ∞\n• Количество устройств: 3 📱\n• Стоимость: от 149 ₽",
        reply_markup=get_back_keyboard(back_target="menu_tariffs")
    )
    await call.answer()


@dp.callback_query(F.data.in_({"partner_invite", "partner_qr", "partner_list", "partner_analytics"}))
async def cb_partner_sub(call: CallbackQuery):
    actions = {
        "partner_invite": "📝 <b>Создание приглашения</b>\n\nСсылка для приглашения сгенерирована.",
        "partner_qr": "📱 <b>QR-код приглашения</b>\n\nQR-код сформирован.",
        "partner_list": "👥 <b>Список ваших рефералов</b>\n\nУ вас пока нет приглашенных пользователей.",
        "partner_analytics": "📊 <b>Детальная аналитика</b>\n\nСтатистика будет доступна после появления рефералов."
    }
    await call.message.edit_text(
        text=actions.get(call.data, "Раздел в разработке"),
        reply_markup=get_back_keyboard(back_target="menu_partner")
    )
    await call.answer()


@dp.callback_query(F.data.in_({"ticket_create", "ticket_list"}))
async def cb_ticket_sub(call: CallbackQuery):
    actions = {
        "ticket_create": "🎫 <b>Создание тикета</b>\n\nОпишите вашу проблему или задайте вопрос сообщением ниже.",
        "ticket_list": "📋 <b>Мои тикеты</b>\n\nУ вас нет активных или завершенных обращений."
    }
    await call.message.edit_text(
        text=actions.get(call.data, "Раздел в разработке"),
        reply_markup=get_back_keyboard(back_target="menu_support")
    )
    await call.answer()


@dp.message()
async def any_other_message(message: Message):
    """При отправке любого текста вне сценария - напоминаем главное меню"""
    name = message.from_user.full_name or "Пользователь"
    await message.answer(
        text=get_main_text(name),
        reply_markup=get_main_keyboard()
    )


# --- ЗАПУСК ---

async def main():
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    print("--------------------------------------------------")
    print("VPN UI Бот успешно запущен и готов к работе!")
    print("--------------------------------------------------")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")
