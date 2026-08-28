import aiosqlite
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import config

DB_PATH = "bot.db"


async def init_db():
    """Инициализация таблиц базы данных и дефолтных настроек"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                balance INTEGER DEFAULT 0,
                referrer_id INTEGER,
                partner_referrer_id INTEGER,
                referral_count INTEGER DEFAULT 0,
                trial_used INTEGER DEFAULT 0,
                sub_active_until TIMESTAMP,
                sub_plan TEXT,
                vpn_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                text TEXT NOT NULL,
                status TEXT DEFAULT 'open', -- 'open', 'answered', 'closed'
                admin_reply TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                reward_type TEXT NOT NULL, -- 'balance' или 'days'
                reward_value INTEGER NOT NULL,
                max_activations INTEGER DEFAULT 100,
                activations_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS promocode_activations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL,
                first_deposit_bonus_given INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tx_type TEXT NOT NULL, -- 'deposit', 'purchase', 'referral', 'promocode', 'trial'
                amount INTEGER NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                is_admin INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                invoice_type TEXT NOT NULL, -- 'deposit' или 'subscription'
                plan_key TEXT,
                days INTEGER DEFAULT 0,
                amount INTEGER NOT NULL,
                pay_url TEXT NOT NULL,
                provider TEXT DEFAULT 'cryptobot', -- 'cryptobot' или 'freekassa'
                status TEXT DEFAULT 'active', -- 'active', 'paid', 'expired'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        try:
            await db.execute("ALTER TABLE admins ADD COLUMN is_admin INTEGER DEFAULT 1")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE invoices ADD COLUMN provider TEXT DEFAULT 'cryptobot'")
        except Exception:
            pass

        try:
            await db.execute("""
                UPDATE users 
                SET vpn_key = REPLACE(REPLACE(vpn_key, 'type=tcp', 'type=xhttp&path=%2F&mode=auto'), 'type=http', 'type=xhttp')
                WHERE vpn_key LIKE '%type=tcp%'
            """)
        except Exception:
            pass

        # Инициализируем дефолтные цены
        defaults = {
            "price_1_month": str(config.PRICE_STANDARD_1_MONTH),
            "price_3_months": str(config.PRICE_STANDARD_3_MONTHS),
            "price_6_months": str(config.PRICE_STANDARD_6_MONTHS),
            "price_12_months": str(config.PRICE_STANDARD_12_MONTHS),
        }
        for k, v in defaults.items():
            await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

        # Добавляем админов из config.ADMIN_IDS
        for aid in config.ADMIN_IDS:
            if aid > 0:
                await db.execute("INSERT OR IGNORE INTO admins (user_id, is_admin) VALUES (?, 1)", (aid,))

        await db.commit()


# --- PRICES & SETTINGS ---

async def get_prices() -> dict:
    """Вернуть актуальные цены на тарифы из БД"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT key, value FROM settings WHERE key LIKE 'price_%'")
        rows = await cursor.fetchall()
        prices = {k: int(v) for k, v in rows}

    return {
        "price_1_month": prices.get("price_1_month", config.PRICE_STANDARD_1_MONTH),
        "price_3_months": prices.get("price_3_months", config.PRICE_STANDARD_3_MONTHS),
        "price_6_months": prices.get("price_6_months", config.PRICE_STANDARD_6_MONTHS),
        "price_12_months": prices.get("price_12_months", config.PRICE_STANDARD_12_MONTHS),
    }


async def set_price(plan_key: str, price: int):
    """Установить новую цену для тарифа"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (plan_key, str(price))
        )
        await db.commit()


# --- USERS ---

async def get_or_create_user(user_id: int, username: str = "", full_name: str = "") -> dict:
    """Получить или создать пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                (username or row["username"], full_name or row["full_name"], user_id)
            )
            await db.commit()
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return dict(await cursor.fetchone())
        else:
            await db.execute(
                "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                (user_id, username, full_name)
            )
            await db.commit()
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return dict(await cursor.fetchone())


async def get_user(user_id: int) -> Optional[dict]:
    """Получить данные пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_balance(user_id: int, delta: int) -> int:
    """Изменить баланс пользователя на delta"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (delta, user_id)
        )
        await db.commit()
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def activate_subscription(user_id: int, days: int, plan_name: str, vpn_key: str = None) -> datetime:
    """Активировать или продлить подписку"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT sub_active_until, vpn_key FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()

        now = datetime.now()
        current_until = None
        if row and row["sub_active_until"]:
            try:
                current_until = datetime.fromisoformat(row["sub_active_until"])
            except Exception:
                current_until = None

        if current_until and current_until > now:
            new_until = current_until + timedelta(days=days)
        else:
            new_until = now + timedelta(days=days)

        new_key = vpn_key or (row["vpn_key"] if row else None)

        await db.execute(
            """UPDATE users SET
                sub_active_until = ?,
                sub_plan = ?,
                vpn_key = ?
            WHERE user_id = ?""",
            (new_until.isoformat(), plan_name, new_key, user_id)
        )
        await db.commit()
        return new_until


async def use_trial_subscription(user_id: int, days: int, vpn_key: str = None) -> Optional[datetime]:
    """Активировать пробный период (если еще не использован)"""
    user = await get_user(user_id)
    if not user or user.get("trial_used"):
        return None

    until = await activate_subscription(user_id, days, "Тестовый", vpn_key)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET trial_used = 1 WHERE user_id = ?", (user_id,))
        await db.commit()
    await add_transaction(user_id, "trial", 0, f"Активация пробного периода на {days} дн.")
    return until


# --- REFERRALS ---

async def set_referrer(user_id: int, referrer_id: int) -> bool:
    """Установить пригласившего пользователя"""
    if user_id == referrer_id:
        return False

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row or row["referrer_id"] is not None:
            return False

        ref_cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_id,))
        if not await ref_cursor.fetchone():
            return False

        await db.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (referrer_id, user_id))
        await db.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (referrer_id,))
        await db.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, user_id))
        await db.commit()
        return True


async def get_referral_stats(user_id: int) -> dict:
    """Получить реферальную статистику пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        c1 = await db.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
        total_invited = (await c1.fetchone())[0]

        c2 = await db.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND first_deposit_bonus_given = 1", (user_id,))
        first_deposits = (await c2.fetchone())[0]

        c3 = await db.execute("SELECT COALESCE(SUM(total_earned), 0) FROM referrals WHERE referrer_id = ?", (user_id,))
        total_earned = (await c3.fetchone())[0]

        month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        c4 = await db.execute("SELECT COALESCE(SUM(total_earned), 0) FROM referrals WHERE referrer_id = ? AND created_at >= ?", (user_id, month_ago))
        month_earned = (await c4.fetchone())[0]

        conversion = round((first_deposits / total_invited * 100), 1) if total_invited > 0 else 0

        return {
            "total_invited": total_invited,
            "first_deposits": first_deposits,
            "active_referrals": total_invited,
            "conversion": conversion,
            "total_earned": total_earned,
            "month_earned": month_earned,
        }


async def get_referral_list(user_id: int) -> List[dict]:
    """Список рефералов"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT u.user_id, u.username, u.full_name, r.created_at, r.total_earned
            FROM referrals r
            JOIN users u ON r.referred_id = u.user_id
            WHERE r.referrer_id = ?
            ORDER BY r.created_at DESC
            LIMIT 30
        """, (user_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# --- TICKETS ---

async def create_ticket(user_id: int, username: str, full_name: str, text: str) -> int:
    """Создать новый тикет в техподдержку"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO tickets (user_id, username, full_name, text, status)
               VALUES (?, ?, ?, ?, 'open')""",
            (user_id, username, full_name, text)
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_tickets(user_id: int) -> List[dict]:
    """Получить все тикеты пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC LIMIT 15",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_ticket(ticket_id: int) -> Optional[dict]:
    """Получить конкретный тикет"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_open_tickets() -> List[dict]:
    """Получить все открытые тикеты"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tickets WHERE status = 'open' ORDER BY created_at ASC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_all_tickets(limit: int = 30) -> List[dict]:
    """Получить список всех тикетов"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tickets ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def reply_ticket(ticket_id: int, admin_reply: str) -> bool:
    """Ответить на тикет и перевести в статус answered"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE tickets SET
                admin_reply = ?,
                status = 'answered',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?""",
            (admin_reply, ticket_id)
        )
        await db.commit()
        return True


async def close_ticket(ticket_id: int) -> bool:
    """Закрыть тикет"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tickets SET status = 'closed', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (ticket_id,)
        )
        await db.commit()
        return True


# --- PROMOCODES ---

async def create_promocode(code: str, reward_type: str, reward_value: int, max_activations: int = 100) -> bool:
    """Создать промокод"""
    clean_code = code.strip().upper()
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                """INSERT INTO promocodes (code, reward_type, reward_value, max_activations)
                   VALUES (?, ?, ?, ?)""",
                (clean_code, reward_type, reward_value, max_activations)
            )
            await db.commit()
            return True
        except Exception:
            return False


async def activate_promocode(code: str, user_id: int) -> dict:
    """Активировать промокод пользователем"""
    clean_code = code.strip().upper()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("SELECT * FROM promocodes WHERE code = ?", (clean_code,))
        promo = await cursor.fetchone()
        if not promo:
            return {"success": False, "msg": "Промокод не найден."}

        promo = dict(promo)
        if promo["activations_count"] >= promo["max_activations"]:
            return {"success": False, "msg": "Лимит активаций этого промокода исчерпан."}

        act_cursor = await db.execute(
            "SELECT id FROM promocode_activations WHERE code = ? AND user_id = ?",
            (clean_code, user_id)
        )
        if await act_cursor.fetchone():
            return {"success": False, "msg": "Вы уже активировали данный промокод."}

        reward_type = promo["reward_type"]
        reward_val = promo["reward_value"]

        if reward_type == "balance":
            await update_balance(user_id, reward_val)
            await add_transaction(user_id, "promocode", reward_val, f"Активация промокода {clean_code}")
            reward_desc = f"{reward_val} ₽ на баланс"
        elif reward_type == "days":
            await activate_subscription(user_id, reward_val, "Промокод")
            await add_transaction(user_id, "promocode", 0, f"Промокод {clean_code} (+{reward_val} дн. подписки)")
            reward_desc = f"+{reward_val} дней подписки"
        else:
            reward_desc = "Бонус активирован"

        await db.execute(
            "INSERT INTO promocode_activations (code, user_id) VALUES (?, ?)",
            (clean_code, user_id)
        )
        await db.execute(
            "UPDATE promocodes SET activations_count = activations_count + 1 WHERE code = ?",
            (clean_code,)
        )
        await db.commit()

        return {"success": True, "reward_desc": reward_desc}


# --- TRANSACTIONS ---

async def add_transaction(user_id: int, tx_type: str, amount: int, description: str):
    """Добавить запись об операции"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO transactions (user_id, tx_type, amount, description)
               VALUES (?, ?, ?, ?)""",
            (user_id, tx_type, amount, description)
        )
        await db.commit()


async def get_user_transactions(user_id: int) -> List[dict]:
    """Получить историю операций пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 15",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# --- ADMINS & STATS ---

async def is_admin_user(user_id: int) -> bool:
    """Проверка прав администратора (по ID из config или таблицы admins)"""
    if user_id in config.ADMIN_IDS:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM admins WHERE user_id = ? AND is_admin = 1", (user_id,))
        row = await cursor.fetchone()
        return bool(row)


async def add_admin_id(user_id: int):
    """Добавить ID администратора"""
    if user_id not in config.ADMIN_IDS:
        config.ADMIN_IDS.append(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO admins (user_id, is_admin) VALUES (?, 1)", (user_id,))
        await db.commit()


async def get_all_admins() -> List[int]:
    """Получить список всех ID администраторов"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM admins WHERE is_admin = 1")
        rows = await cursor.fetchall()
        db_admins = [r[0] for r in rows]
    all_admins = set(config.ADMIN_IDS + db_admins)
    return [a for a in all_admins if a > 0]


async def get_global_stats() -> dict:
    """Глобальная статистика для админа"""
    async with aiosqlite.connect(DB_PATH) as db:
        c1 = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await c1.fetchone())[0]

        now_iso = datetime.now().isoformat()
        c2 = await db.execute("SELECT COUNT(*) FROM users WHERE sub_active_until > ?", (now_iso,))
        active_subs = (await c2.fetchone())[0]

        c3 = await db.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'")
        open_tickets = (await c3.fetchone())[0]

        c4 = await db.execute("SELECT COALESCE(SUM(balance), 0) FROM users")
        total_balance = (await c4.fetchone())[0]

        return {
            "total_users": total_users,
            "active_subs": active_subs,
            "open_tickets": open_tickets,
            "total_balance": total_balance,
        }


# --- INVOICES & PAYMENTS ---

async def create_db_invoice(
    invoice_id: int,
    user_id: int,
    invoice_type: str,
    plan_key: str,
    days: int,
    amount: int,
    pay_url: str,
    provider: str = "cryptobot"
):
    """Сохранить счет на оплату в БД"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO invoices
               (invoice_id, user_id, invoice_type, plan_key, days, amount, pay_url, provider, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')""",
            (invoice_id, user_id, invoice_type, plan_key, days, amount, pay_url, provider)
        )
        await db.commit()


async def get_db_invoice(invoice_id: int) -> Optional[dict]:
    """Получить счет из БД"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def mark_invoice_paid(invoice_id: int) -> Optional[dict]:
    """Пометить счет как оплаченный (возвращает данные счета, если он еще не был оплачен)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,))
        row = await cursor.fetchone()
        if not row:
            return None

        invoice = dict(row)
        if invoice["status"] == "paid":
            return None  # Уже обработан ранее

        await db.execute("UPDATE invoices SET status = 'paid' WHERE invoice_id = ?", (invoice_id,))
        await db.commit()
        return invoice


async def process_paid_invoice(invoice_id: int, bot=None) -> Optional[dict]:
    """
    Универсальная обработка оплаченного счета (пополнение баланса или активация подписки,
    начисление реферальных бонусов и отправка уведомлений в Telegram).
    """
    invoice = await mark_invoice_paid(invoice_id)
    if not invoice:
        return None

    user_id = invoice["user_id"]
    inv_type = invoice["invoice_type"]
    amount = invoice["amount"]
    provider = invoice.get("provider", "cryptobot")
    provider_name = "FreeKassa (Карты/СБП)" if provider == "freekassa" else "CryptoBot"

    # Реферальный бонус
    ref_info = await process_referral_reward_on_payment(user_id, amount)
    if ref_info and bot:
        try:
            import html
            await bot.send_message(
                chat_id=ref_info["referrer_id"],
                text=(
                    f"🎁 <b>Начислен реферальный бонус!</b>\n\n"
                    f"Ваш приглашенный друг <b>{html.escape(str(ref_info['user_name']))}</b> совершил оплату.\n"
                    f"Вам начислено <b>+{ref_info['bonus_amount']} ₽</b> на баланс!"
                )
            )
        except Exception:
            pass

    if inv_type == "deposit":
        new_balance = await update_balance(user_id, amount)
        await add_transaction(user_id, "deposit", amount, f"Пополнение баланса через {provider_name}")

        if bot:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🎉 <b>Оплата успешно подтверждена!</b>\n\n"
                        f"💰 На ваш баланс зачислено <b>+{amount} ₽</b> через {provider_name}.\n"
                        f"Текущий баланс: <b>{new_balance} ₽</b>."
                    )
                )
            except Exception:
                pass

        return {
            "type": "deposit",
            "user_id": user_id,
            "amount": amount,
            "new_balance": new_balance,
            "provider": provider
        }

    elif inv_type == "subscription":
        from services.xui_service import XUIService
        days = invoice.get("days", 30) or 30
        plan_key = invoice.get("plan_key") or "Стандартный"

        vpn_data = await XUIService.create_or_extend_client(user_id, days)
        vpn_link = vpn_data.get("link", "") if isinstance(vpn_data, dict) else str(vpn_data)

        active_until = await activate_subscription(user_id, days, "Стандартный", vpn_link)
        await add_transaction(user_id, "purchase", -amount, f"Покупка тарифа «Стандартный» ({days} дн.) через {provider_name}")

        if bot:
            try:
                import html
                until_str = active_until.strftime("%d.%m.%Y %H:%M") if hasattr(active_until, "strftime") else str(active_until)
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🎉 <b>Подписка успешно оплачена и активирована!</b>\n\n"
                        f"• <b>Тариф:</b> {plan_key}\n"
                        f"• <b>Срок действия:</b> до <b>{until_str}</b> ({days} дн.)\n"
                        f"• <b>Способ оплаты:</b> {provider_name}\n\n"
                        f"🔑 <b>Ваш ключ подключения:</b>\n"
                        f"<code>{html.escape(vpn_link)}</code>\n\n"
                        f"📖 <b>Инструкция:</b> скопируйте ключ и вставьте в клиент (V2rayN, V2Box, Happ)."
                    )
                )
            except Exception:
                pass

        return {
            "type": "subscription",
            "user_id": user_id,
            "amount": amount,
            "active_until": active_until,
            "vpn_link": vpn_link,
            "provider": provider
        }


async def process_referral_reward_on_payment(user_id: int, payment_amount: int) -> Optional[dict]:
    """Начислить реферальный бонус рефереру при первом пополнении/покупке"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT referrer_id, full_name, username FROM users WHERE user_id = ?", (user_id,))
        user_row = await cursor.fetchone()
        if not user_row or not user_row["referrer_id"]:
            return None

        referrer_id = user_row["referrer_id"]
        ref_cursor = await db.execute(
            "SELECT id, first_deposit_bonus_given FROM referrals WHERE referrer_id = ? AND referred_id = ?",
            (referrer_id, user_id)
        )
        ref_record = await ref_cursor.fetchone()
        if not ref_record or ref_record["first_deposit_bonus_given"] == 1:
            return None  # Бонус за первое пополнение уже выдавался

        # Начисляем бонус
        bonus_rub = config.REFERRAL_BONUS_RUB
        percent_bonus = int(payment_amount * (config.REFERRAL_PERCENT / 100.0))
        total_bonus = bonus_rub + percent_bonus

        if total_bonus > 0:
            await update_balance(referrer_id, total_bonus)
            await add_transaction(
                referrer_id,
                "referral",
                total_bonus,
                f"Бонус за первое пополнение друга {user_row['full_name'] or user_id}"
            )
            await db.execute(
                """UPDATE referrals SET
                    first_deposit_bonus_given = 1,
                    total_earned = total_earned + ?
                WHERE referrer_id = ? AND referred_id = ?""",
                (total_bonus, referrer_id, user_id)
            )
            await db.commit()

            return {
                "referrer_id": referrer_id,
                "bonus_amount": total_bonus,
                "user_name": user_row["full_name"] or user_row["username"] or str(user_id)
            }

    return None

