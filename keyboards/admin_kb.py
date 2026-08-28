from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict

def admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура панели администратора"""
    buttons = [
        [
            InlineKeyboardButton(text="💰 Управление ценами", callback_data="admin_prices"),
            InlineKeyboardButton(text="🎫 Управление тикетами", callback_data="admin_tickets")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="🎁 Создать промокод", callback_data="admin_create_promo")
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="👥 Управление админами", callback_data="admin_list_admins")
        ],
        [
            InlineKeyboardButton(text="⬅️ В клиентское меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_prices_keyboard(prices: dict) -> InlineKeyboardMarkup:
    """Клавиатура управления ценами тарифов"""
    buttons = [
        [InlineKeyboardButton(text=f"1 месяц — {prices['price_1_month']} ₽ ✏️", callback_data="admin_set_price:price_1_month")],
        [InlineKeyboardButton(text=f"3 месяца — {prices['price_3_months']} ₽ ✏️", callback_data="admin_set_price:price_3_months")],
        [InlineKeyboardButton(text=f"6 месяцев — {prices['price_6_months']} ₽ ✏️", callback_data="admin_set_price:price_6_months")],
        [InlineKeyboardButton(text=f"12 месяцев — {prices['price_12_months']} ₽ ✏️", callback_data="admin_set_price:price_12_months")],
        [InlineKeyboardButton(text="⬅️ В панель админа", callback_data="admin_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_tickets_list_keyboard(tickets: List[dict], show_all: bool = False) -> InlineKeyboardMarkup:
    """Список тикетов с кнопками для быстрого перехода"""
    buttons = []
    for t in tickets[:10]:
        status_icon = "⏳" if t["status"] == "open" else "✅"
        uname = f"@{t['username']}" if t.get("username") else f"ID:{t['user_id']}"
        label = f"{status_icon} #{t['id']} {uname}: {t['text'][:20]}..."
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"admin_view_ticket:{t['id']}")])

    nav_row = [
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_tickets"),
    ]
    if not show_all:
        nav_row.append(InlineKeyboardButton(text="📋 Все тикеты", callback_data="admin_all_tickets"))
    else:
        nav_row.append(InlineKeyboardButton(text="⏳ Только открытые", callback_data="admin_tickets"))

    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton(text="⬅️ В панель админа", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_ticket_actions_keyboard(ticket_id: int, is_open: bool = True) -> InlineKeyboardMarkup:
    """Действия над конкретным тикетом"""
    buttons = []
    if is_open:
        buttons.append([
            InlineKeyboardButton(text="✉️ Ответить пользователю", callback_data=f"admin_reply_ticket:{ticket_id}"),
            InlineKeyboardButton(text="🔒 Закрыть", callback_data=f"admin_close_ticket:{ticket_id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="✉️ Ответить повторно", callback_data=f"admin_reply_ticket:{ticket_id}")
        ])

    buttons.append([InlineKeyboardButton(text="⬅️ К списку тикетов", callback_data="admin_tickets")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_admins_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления списком администраторов"""
    buttons = [
        [InlineKeyboardButton(text="➕ Добавить админа по ID", callback_data="admin_add_admin")],
        [InlineKeyboardButton(text="⬅️ В панель админа", callback_data="admin_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_back_keyboard(back_target: str = "admin_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_target)]
    ])
