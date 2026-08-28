import html
import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

import time
import config
import database.db as db
from services.xui_service import XUIService
from services.cryptopay_service import CryptoPayService
from services.freekassa_service import FreeKassaService
from keyboards.user_kb import (
    tariffs_keyboard,
    tariff_periods_keyboard,
    buy_payment_options_keyboard,
    payment_invoice_keyboard,
    back_keyboard
)

logger = logging.getLogger(__name__)
router = Router()

PERIODS_CONFIG = {
    "1": (30, "price_1_month", "1 месяц"),
    "3": (90, "price_3_months", "3 месяца"),
    "6": (180, "price_6_months", "6 месяцев"),
    "12": (365, "price_12_months", "12 месяцев (1 год)"),
}


@router.callback_query(F.data == "menu_trial")
async def cb_trial(call: CallbackQuery):
    """Активация тестовой подписки"""
    user_id = call.from_user.id
    user = await db.get_user(user_id)

    if user and user.get("trial_used"):
        await call.message.edit_text(
            "❌ <b>Вы уже использовали тестовую подписку.</b>\n\n"
            "Для продолжения использования VPN выберите подходящий тариф в разделе «💎 Купить подписку».",
            reply_markup=back_keyboard()
        )
        await call.answer()
        return

    # Создаем тестовый клиент в 3x-ui
    vpn_data = await XUIService.create_or_extend_client(user_id, config.TRIAL_DAYS)
    vpn_link = vpn_data.get("link", "")

    # Активируем в базе
    active_until = await db.use_trial_subscription(user_id, config.TRIAL_DAYS, vpn_link)

    text = (
        f"🎉 <b>Тестовая подписка успешно активирована на {config.TRIAL_DAYS} дн.!</b>\n\n"
        f"📅 Активна до: <b>{active_until.strftime('%d.%m.%Y %H:%M')}</b>\n\n"
        f"🔑 <b>Ваш ключ подключения:</b>\n"
        f"<code>{html.escape(vpn_link)}</code>\n\n"
        f"📖 <b>Как подключиться:</b>\n"
        f"1. Скопируйте ключ выше (нажатием на него).\n"
        f"2. Вставьте в приложение VPN (V2rayN, V2Box, Happ).\n"
        f"3. Включите подключение."
    )
    await call.message.edit_text(text=text, reply_markup=back_keyboard())
    await call.answer()


@router.callback_query(F.data == "menu_tariffs")
async def cb_tariffs(call: CallbackQuery):
    """Экран выбора тарифов"""
    prices = await db.get_prices()
    text = (
        "📦 <b>Выберите тариф</b>\n\n"
        f"<b>Стандартный — ∞ / 3 📱  от {prices['price_1_month']}₽</b>\n"
        "<i>Базовый тарифный план</i>"
    )
    await call.message.edit_text(text=text, reply_markup=tariffs_keyboard())
    await call.answer()


@router.callback_query(F.data == "tariff_standard")
async def cb_tariff_standard(call: CallbackQuery):
    """Выбор периода для тарифа Стандартный"""
    prices = await db.get_prices()
    text = (
        "📦 <b>Тариф «Стандартный»</b>\n\n"
        "• <b>Трафик:</b> Безлимитный (∞)\n"
        "• <b>Устройств:</b> До 3 одновременно 📱\n"
        "• <b>Скорость:</b> До 1 Гбит/с\n\n"
        "Выберите срок подписки:"
    )
    await call.message.edit_text(text=text, reply_markup=tariff_periods_keyboard(prices))
    await call.answer()


@router.callback_query(F.data.startswith("buy_period_"))
async def cb_buy_period(call: CallbackQuery):
    """Выбор способа оплаты для выбранного срока"""
    period_key = call.data.replace("buy_period_", "")
    days, price_key, label = PERIODS_CONFIG.get(period_key, (30, "price_1_month", "1 месяц"))

    prices = await db.get_prices()
    price = prices.get(price_key, 149)

    user = await db.get_user(call.from_user.id)
    balance = user.get("balance", 0) if user else 0

    text = (
        f"💎 <b>Оформление подписки</b>\n\n"
        f"• <b>Тариф:</b> Стандартный\n"
        f"• <b>Срок:</b> {label} ({days} дн.)\n"
        f"• <b>Стоимость:</b> <b>{price} ₽</b>\n"
        f"• <b>Ваш баланс:</b> {balance} ₽\n\n"
        "Выберите удобный способ оплаты:"
    )
    await call.message.edit_text(
        text=text,
        reply_markup=buy_payment_options_keyboard(period_key, price, balance)
    )
    await call.answer()


@router.callback_query(F.data.startswith("pay_with_balance:"))
async def cb_pay_with_balance(call: CallbackQuery, bot: Bot):
    """Оплата тарифа с внутреннего баланса"""
    period_key = call.data.split("pay_with_balance:")[1]
    days, price_key, label = PERIODS_CONFIG.get(period_key, (30, "price_1_month", "1 месяц"))

    prices = await db.get_prices()
    price = prices.get(price_key, 149)

    user_id = call.from_user.id
    user = await db.get_user(user_id)
    balance = user.get("balance", 0) if user else 0

    if balance < price:
        await call.answer("Недостаточно средств на балансе!", show_alert=True)
        return

    # Списываем баланс
    await db.update_balance(user_id, -price)

    # Создаем/продлеваем в 3x-ui
    vpn_data = await XUIService.create_or_extend_client(user_id, days)
    vpn_link = vpn_data.get("link", "")

    # Активируем подписку в БД
    active_until = await db.activate_subscription(user_id, days, "Стандартный", vpn_link)
    await db.add_transaction(user_id, "purchase", -price, f"Покупка тарифа «Стандартный» на {label}")

    # Проверяем реферальный бонус за первую оплату
    ref_info = await db.process_referral_reward_on_payment(user_id, price)
    if ref_info:
        try:
            await bot.send_message(
                chat_id=ref_info["referrer_id"],
                text=(
                    f"🎁 <b>Начислен реферальный бонус!</b>\n\n"
                    f"Ваш приглашенный друг <b>{html.escape(ref_info['user_name'])}</b> совершил оплату.\n"
                    f"Вам начислено <b>+{ref_info['bonus_amount']} ₽</b> на баланс!"
                )
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление рефереру {ref_info['referrer_id']}: {e}")

    text = (
        f"🎉 <b>Подписка успешно оформлена!</b>\n\n"
        f"• <b>Тариф:</b> Стандартный\n"
        f"• <b>Срок:</b> {label}\n"
        f"• <b>Активна до:</b> <b>{active_until.strftime('%d.%m.%Y %H:%M')}</b>\n\n"
        f"🔑 <b>Ваш ключ подключения:</b>\n"
        f"<code>{html.escape(vpn_link)}</code>\n\n"
        f"📖 <b>Инструкция:</b> скопируйте ключ и вставьте в VPN приложение (V2rayN, V2Box, Happ)."
    )
    await call.message.edit_text(text=text, reply_markup=back_keyboard())
    await call.answer("Оплата с баланса прошла успешно!", show_alert=True)


@router.callback_query(F.data.startswith("pay_with_crypto:"))
async def cb_pay_with_crypto(call: CallbackQuery):
    """Оплата тарифа напрямую через CryptoBot"""
    period_key = call.data.split("pay_with_crypto:")[1]
    days, price_key, label = PERIODS_CONFIG.get(period_key, (30, "price_1_month", "1 месяц"))

    prices = await db.get_prices()
    price = prices.get(price_key, 149)

    user_id = call.from_user.id

    invoice = await CryptoPayService.create_invoice(
        amount_rub=price,
        description=f"Оплата VPN «Стандартный» на {label}",
        payload=f"sub_{user_id}_{period_key}"
    )

    if not invoice:
        await call.answer("Не удалось сформировать счет. Попробуйте позже.", show_alert=True)
        return

    # Сохраняем в базу
    await db.create_db_invoice(
        invoice_id=invoice["invoice_id"],
        user_id=user_id,
        invoice_type="subscription",
        plan_key="Стандартный",
        days=days,
        amount=price,
        pay_url=invoice["pay_url"]
    )

    text = (
        f"🧾 <b>Счет на оплату подписки #{invoice['invoice_id']}</b>\n\n"
        f"• <b>Тариф:</b> Стандартный ({label})\n"
        f"• <b>Сумма к оплате:</b> {price} ₽\n"
        f"• <b>Способ оплаты:</b> @CryptoBot\n\n"
        "Нажмите кнопку ниже для перехода к оплате. "
        "После оплаты нажмите <b>«🔄 Проверить оплату»</b> для мгновенной выдачи ключа."
    )
    await call.message.edit_text(
        text=text,
        reply_markup=payment_invoice_keyboard(invoice["pay_url"], invoice["invoice_id"], provider="cryptobot", back_target="tariff_standard")
    )
    await call.answer()


@router.callback_query(F.data.startswith("pay_with_freekassa:"))
async def cb_pay_with_freekassa(call: CallbackQuery):
    """Оплата тарифа картой / СБП через FreeKassa"""
    period_key = call.data.split("pay_with_freekassa:")[1]
    days, price_key, label = PERIODS_CONFIG.get(period_key, (30, "price_1_month", "1 месяц"))

    prices = await db.get_prices()
    price = prices.get(price_key, 149)

    user_id = call.from_user.id
    order_id = int(time.time() * 1000) % 2147483647

    pay_url = FreeKassaService.generate_payment_url(
        order_id=order_id,
        amount=price,
        currency="RUB"
    )

    # Сохраняем в базу
    await db.create_db_invoice(
        invoice_id=order_id,
        user_id=user_id,
        invoice_type="subscription",
        plan_key="Стандартный",
        days=days,
        amount=price,
        pay_url=pay_url,
        provider="freekassa"
    )

    text = (
        f"🧾 <b>Счет на оплату подписки #{order_id}</b>\n\n"
        f"• <b>Тариф:</b> Стандартный ({label})\n"
        f"• <b>Сумма к оплате:</b> {price} ₽\n"
        f"• <b>Способ оплаты:</b> Банковские карты РФ / СБП (FreeKassa)\n\n"
        "Нажмите кнопку ниже для перехода к оплате. "
        "После оплаты подписка активируется автоматически, или нажмите <b>«🔄 Проверить оплату»</b>."
    )
    await call.message.edit_text(
        text=text,
        reply_markup=payment_invoice_keyboard(pay_url, order_id, provider="freekassa", back_target="tariff_standard")
    )
    await call.answer()
