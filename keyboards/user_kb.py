from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import config

def main_keyboard(balance: int = 0, has_active_sub: bool = False) -> InlineKeyboardMarkup:
    """Главное меню"""
    buttons = []

    # Кнопка Mini App (если WEBAPP_URL задан)
    webapp_url = getattr(config, 'WEBAPP_URL', '')
    if webapp_url:
        buttons.append([
            InlineKeyboardButton(
                text="📱 Открыть приложение",
                web_app=WebAppInfo(url=f"{webapp_url}/webapp/index.html")
            )
        ])

    buttons.extend([
        [
            InlineKeyboardButton(text=f"💰 Баланс: {balance} ₽", callback_data="menu_balance")
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
    ])
    if has_active_sub:
        idx = 2 if webapp_url else 1
        buttons.insert(idx, [InlineKeyboardButton(text="🔑 Мой ключ подключения", callback_data="my_vpn_key")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channel_subscription_keyboard(channel_url: str = None) -> InlineKeyboardMarkup:
    """Клавиатура проверки обязательной подписки на канал"""
    url = channel_url or getattr(config, 'CHANNEL_URL', 'https://t.me/Ershvpn')
    buttons = [
        [
            InlineKeyboardButton(text="📢 Подписаться на канал", url=url)
        ],
        [
            InlineKeyboardButton(text="🔄 Я подписался / Проверить", callback_data="check_channel_sub")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def balance_keyboard() -> InlineKeyboardMarkup:
    """Меню раздела баланса"""
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


def payment_method_keyboard(back_target: str = "menu_balance") -> InlineKeyboardMarkup:
    """Выбор способа пополнения баланса"""
    buttons = [
        [
            InlineKeyboardButton(text="💳 Карты РФ / СБП (FreeKassa)", callback_data="deposit_method:freekassa")
        ],
        [
            InlineKeyboardButton(text="⚡ CryptoBot (USDT, TON, BTC)", callback_data="deposit_method:cryptobot")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data=back_target)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def deposit_options_keyboard(method: str = "cryptobot") -> InlineKeyboardMarkup:
    """Выбор суммы для пополнения баланса"""
    buttons = [
        [
            InlineKeyboardButton(text="150 ₽", callback_data=f"deposit_amount:{method}:150"),
            InlineKeyboardButton(text="300 ₽", callback_data=f"deposit_amount:{method}:300"),
            InlineKeyboardButton(text="500 ₽", callback_data=f"deposit_amount:{method}:500")
        ],
        [
            InlineKeyboardButton(text="1000 ₽", callback_data=f"deposit_amount:{method}:1000"),
            InlineKeyboardButton(text="2000 ₽", callback_data=f"deposit_amount:{method}:2000")
        ],
        [
            InlineKeyboardButton(text="✏️ Другая сумма", callback_data=f"deposit_custom:{method}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="sub_deposit")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_invoice_keyboard(
    pay_url: str,
    invoice_id: int,
    provider: str = "cryptobot",
    back_target: str = "menu_balance"
) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой оплаты и кнопкой проверки статуса счета"""
    if provider == "freekassa":
        pay_btn_text = "💳 Оплатить картой / СБП ↗"
        check_cb = f"check_fk_invoice:{invoice_id}"
    else:
        pay_btn_text = "⚡ Оплатить через CryptoBot ↗"
        check_cb = f"check_invoice:{invoice_id}"

    buttons = [
        [
            InlineKeyboardButton(text=pay_btn_text, url=pay_url)
        ],
        [
            InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=check_cb)
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data=back_target)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def tariffs_keyboard() -> InlineKeyboardMarkup:
    """Меню выбора тарифов"""
    buttons = [
        [
            InlineKeyboardButton(text="Стандартный", callback_data="tariff_standard")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def tariff_periods_keyboard(prices: dict = None) -> InlineKeyboardMarkup:
    """Меню периодов подписки для выбранного тарифа с актуальными ценами"""
    if not prices:
        prices = {
            "price_1_month": config.PRICE_STANDARD_1_MONTH,
            "price_3_months": config.PRICE_STANDARD_3_MONTHS,
            "price_6_months": config.PRICE_STANDARD_6_MONTHS,
            "price_12_months": config.PRICE_STANDARD_12_MONTHS,
        }
    buttons = [
        [InlineKeyboardButton(text=f"1 месяц — {prices.get('price_1_month', config.PRICE_STANDARD_1_MONTH)} ₽", callback_data="buy_period_1")],
        [InlineKeyboardButton(text=f"3 месяца — {prices.get('price_3_months', config.PRICE_STANDARD_3_MONTHS)} ₽", callback_data="buy_period_3")],
        [InlineKeyboardButton(text=f"6 месяцев — {prices.get('price_6_months', config.PRICE_STANDARD_6_MONTHS)} ₽", callback_data="buy_period_6")],
        [InlineKeyboardButton(text=f"12 месяцев — {prices.get('price_12_months', config.PRICE_STANDARD_12_MONTHS)} ₽", callback_data="buy_period_12")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_tariffs")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def buy_payment_options_keyboard(period: str, price: int, user_balance: int) -> InlineKeyboardMarkup:
    """Выбор способа оплаты для покупки тарифа (с баланса, через FreeKassa или через CryptoBot)"""
    buttons = []
    if user_balance >= price:
        buttons.append([
            InlineKeyboardButton(text=f"💰 Оплатить с баланса ({price} ₽)", callback_data=f"pay_with_balance:{period}")
        ])
    else:
        diff = price - user_balance
        buttons.append([
            InlineKeyboardButton(text=f"💳 Не хватает {diff} ₽ (Пополнить)", callback_data="sub_deposit")
        ])

    buttons.append([
        InlineKeyboardButton(text=f"💳 Карты / СБП (FreeKassa) ({price} ₽)", callback_data=f"pay_with_freekassa:{period}")
    ])
    buttons.append([
        InlineKeyboardButton(text=f"⚡ CryptoBot (USDT/TON) ({price} ₽)", callback_data=f"pay_with_crypto:{period}")
    ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад к тарифам", callback_data="tariff_standard")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def info_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню раздела Инфо с юридическими документами"""
    buttons = [
        [InlineKeyboardButton(text="📄 Пользовательское соглашение", callback_data="info_terms")],
        [InlineKeyboardButton(text="🔒 Политика конфиденциальности", callback_data="info_privacy")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def partner_keyboard() -> InlineKeyboardMarkup:
    """Меню партнерки / реферальной программы"""
    buttons = [
        [InlineKeyboardButton(text="📝 Создать приглашение", callback_data="partner_invite")],
        [InlineKeyboardButton(text="📱 Показать QR код", callback_data="partner_qr")],
        [InlineKeyboardButton(text="👥 Список рефералов", callback_data="partner_list")],
        [InlineKeyboardButton(text="📊 Аналитика", callback_data="partner_analytics")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def support_keyboard() -> InlineKeyboardMarkup:
    """Меню техподдержки"""
    buttons = [
        [InlineKeyboardButton(text="🎫 Создать тикет", callback_data="ticket_create")],
        [InlineKeyboardButton(text="📋 Мои тикеты", callback_data="ticket_list")],
        [InlineKeyboardButton(text="💬 Связаться с поддержкой", url=f"https://t.me/{config.SUPPORT_USERNAME}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_keyboard(back_target: str = "main_menu") -> InlineKeyboardMarkup:
    """Универсальная кнопка возврата"""
    buttons = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_target)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_state_keyboard(back_target: str = "main_menu") -> InlineKeyboardMarkup:
    """Кнопка отмены ввода"""
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_to:{back_target}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
