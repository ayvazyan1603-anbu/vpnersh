import html
import time
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import config
import database.db as db
from services.cryptopay_service import CryptoPayService
from services.freekassa_service import FreeKassaService
from services.xui_service import XUIService
from states.user_states import DepositStates
from keyboards.user_kb import (
    balance_keyboard,
    payment_method_keyboard,
    deposit_options_keyboard,
    payment_invoice_keyboard,
    cancel_state_keyboard,
    back_keyboard
)

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu_balance")
async def cb_balance(call: CallbackQuery, state: FSMContext):
    """Экран раздела баланса"""
    await state.clear()
    user = await db.get_user(call.from_user.id)
    balance = user.get("balance", 0) if user else 0

    text = (
        f"💰 <b>Баланс: {balance} ₽</b>\n\n"
        f"Выберите действие:"
    )
    await call.message.edit_text(text=text, reply_markup=balance_keyboard())
    await call.answer()


@router.callback_query(F.data == "sub_history")
async def cb_history(call: CallbackQuery):
    """История операций по счету"""
    transactions = await db.get_user_transactions(call.from_user.id)
    if not transactions:
        text = "📊 <b>История операций:</b>\n\nИстория ваших операций пока пуста."
    else:
        text = "📊 <b>История последних операций:</b>\n\n"
        for tx in transactions:
            sign = "+" if tx["amount"] > 0 else ""
            amount_str = f" ({sign}{tx['amount']} ₽)" if tx["amount"] != 0 else ""
            text += f"• <code>{tx['created_at'][:16]}</code> — {html.escape(tx['description'])}{amount_str}\n"

    await call.message.edit_text(text=text, reply_markup=back_keyboard(back_target="menu_balance"))
    await call.answer()


@router.callback_query(F.data == "sub_deposit")
async def cb_deposit(call: CallbackQuery, state: FSMContext):
    """Выбор способа пополнения баланса"""
    await state.clear()
    text = (
        "💳 <b>Пополнение баланса</b>\n\n"
        "Выберите удобный способ оплаты:\n\n"
        "• <b>Карты РФ / СБП (FreeKassa)</b> — Банковские карты (МИР, Visa, Mastercard), СБП, кошельки.\n"
        "• <b>CryptoBot</b> — Оплата криптовалютой (USDT, TON, BTC, Notcoin, Карты P2P)."
    )
    await call.message.edit_text(text=text, reply_markup=payment_method_keyboard(back_target="menu_balance"))
    await call.answer()


@router.callback_query(F.data.startswith("deposit_method:"))
async def cb_deposit_method(call: CallbackQuery):
    """Выбор суммы пополнения для выбранного метода"""
    method = call.data.split("deposit_method:")[1]
    method_title = "Карты РФ / СБП (FreeKassa)" if method == "freekassa" else "CryptoBot"

    text = (
        f"💳 <b>Пополнение через {method_title}</b>\n\n"
        f"Выберите фиксированную сумму или введите свою:"
    )
    await call.message.edit_text(text=text, reply_markup=deposit_options_keyboard(method=method))
    await call.answer()


@router.callback_query(F.data.startswith("deposit_amount:"))
async def cb_deposit_amount(call: CallbackQuery):
    """Создание счета на фиксированную сумму"""
    parts = call.data.split(":")
    if len(parts) >= 3:
        method = parts[1]
        amount = int(parts[2])
    else:
        method = "cryptobot"
        amount = int(parts[1])

    user_id = call.from_user.id

    if method == "freekassa":
        order_id = int(time.time() * 1000) % 2147483647
        pay_url = FreeKassaService.generate_payment_url(
            order_id=order_id,
            amount=amount,
            currency="RUB"
        )
        await db.create_db_invoice(
            invoice_id=order_id,
            user_id=user_id,
            invoice_type="deposit",
            plan_key="",
            days=0,
            amount=amount,
            pay_url=pay_url,
            provider="freekassa"
        )
        text = (
            f"🧾 <b>Счет на пополнение #{order_id} сформирован!</b>\n\n"
            f"• <b>Сумма к оплате:</b> {amount} ₽\n"
            f"• <b>Способ оплаты:</b> Банковские карты РФ / СБП (FreeKassa)\n\n"
            f"Нажмите кнопку ниже для перехода к оплате. "
            f"После завершения платежа баланс будет пополнен автоматически, или нажмите <b>«🔄 Проверить оплату»</b>."
        )
        await call.message.edit_text(
            text=text,
            reply_markup=payment_invoice_keyboard(pay_url, order_id, provider="freekassa", back_target="sub_deposit")
        )
        await call.answer()

    else:
        # CryptoBot
        invoice = await CryptoPayService.create_invoice(
            amount_rub=amount,
            description=f"Пополнение баланса пользователя {user_id}",
            payload=f"deposit_{user_id}_{amount}"
        )

        if not invoice:
            await call.answer("Не удалось создать счет. Попробуйте позже.", show_alert=True)
            return

        await db.create_db_invoice(
            invoice_id=invoice["invoice_id"],
            user_id=user_id,
            invoice_type="deposit",
            plan_key="",
            days=0,
            amount=amount,
            pay_url=invoice["pay_url"],
            provider="cryptobot"
        )

        text = (
            f"🧾 <b>Счет на пополнение #{invoice['invoice_id']} сформирован!</b>\n\n"
            f"• <b>Сумма к оплате:</b> {amount} ₽\n"
            f"• <b>Способ оплаты:</b> @CryptoBot (USDT, TON, Карты P2P)\n\n"
            f"Нажмите кнопку ниже, чтобы перейти к оплате в CryptoBot. "
            f"После оплаты нажмите <b>«🔄 Проверить оплату»</b>."
        )
        await call.message.edit_text(
            text=text,
            reply_markup=payment_invoice_keyboard(invoice["pay_url"], invoice["invoice_id"], provider="cryptobot", back_target="sub_deposit")
        )
        await call.answer()


@router.callback_query(F.data.startswith("deposit_custom"))
async def cb_deposit_custom(call: CallbackQuery, state: FSMContext):
    """Запрос произвольной суммы пополнения"""
    parts = call.data.split(":")
    method = parts[1] if len(parts) > 1 else "freekassa"
    await state.set_state(DepositStates.waiting_custom_amount)
    await state.update_data(deposit_method=method)

    text = (
        "✏️ <b>Пополнение на произвольную сумму</b>\n\n"
        "Введите желаемую сумму пополнения в рублях (целое число от 10 до 100000):"
    )
    await call.message.edit_text(text=text, reply_markup=cancel_state_keyboard(back_target="sub_deposit"))
    await call.answer()


@router.message(DepositStates.waiting_custom_amount)
async def process_custom_amount(message: Message, state: FSMContext):
    """Обработка введенной суммы"""
    text = message.text.strip()
    if not text.isdigit() or int(text) < 10 or int(text) > 100000:
        await message.answer(
            "❌ Введите корректную сумму в рублях (от 10 до 100 000 ₽):",
            reply_markup=cancel_state_keyboard(back_target="sub_deposit")
        )
        return

    amount = int(text)
    user_id = message.from_user.id
    state_data = await state.get_data()
    method = state_data.get("deposit_method", "freekassa")
    await state.clear()

    if method == "freekassa":
        order_id = int(time.time() * 1000) % 2147483647
        pay_url = FreeKassaService.generate_payment_url(
            order_id=order_id,
            amount=amount,
            currency="RUB"
        )
        await db.create_db_invoice(
            invoice_id=order_id,
            user_id=user_id,
            invoice_type="deposit",
            plan_key="",
            days=0,
            amount=amount,
            pay_url=pay_url,
            provider="freekassa"
        )
        resp_text = (
            f"🧾 <b>Счет на пополнение #{order_id} сформирован!</b>\n\n"
            f"• <b>Сумма к оплате:</b> {amount} ₽\n"
            f"• <b>Способ оплаты:</b> Банковские карты РФ / СБП (FreeKassa)\n\n"
            f"Нажмите кнопку ниже для перехода к оплате. "
            f"После оплаты нажмите <b>«🔄 Проверить оплату»</b>."
        )
        await message.answer(
            text=resp_text,
            reply_markup=payment_invoice_keyboard(pay_url, order_id, provider="freekassa", back_target="sub_deposit")
        )
    else:
        invoice = await CryptoPayService.create_invoice(
            amount_rub=amount,
            description=f"Пополнение баланса пользователя {user_id}",
            payload=f"deposit_{user_id}_{amount}"
        )

        if not invoice:
            await message.answer("❌ Не удалось создать счет. Попробуйте позже.", reply_markup=back_keyboard(back_target="menu_balance"))
            return

        await db.create_db_invoice(
            invoice_id=invoice["invoice_id"],
            user_id=user_id,
            invoice_type="deposit",
            plan_key="",
            days=0,
            amount=amount,
            pay_url=invoice["pay_url"],
            provider="cryptobot"
        )

        resp_text = (
            f"🧾 <b>Счет на пополнение #{invoice['invoice_id']} сформирован!</b>\n\n"
            f"• <b>Сумма к оплате:</b> {amount} ₽\n"
            f"• <b>Способ оплаты:</b> @CryptoBot (USDT, TON, Карты P2P)\n\n"
            f"Нажмите кнопку ниже, чтобы перейти к оплате в CryptoBot. "
            f"После оплаты нажмите <b>«🔄 Проверить оплату»</b>."
        )
        await message.answer(
            text=resp_text,
            reply_markup=payment_invoice_keyboard(invoice["pay_url"], invoice["invoice_id"], provider="cryptobot", back_target="sub_deposit")
        )


@router.callback_query(F.data.startswith("check_invoice:"))
async def cb_check_invoice(call: CallbackQuery, bot: Bot):
    """Проверка статуса оплаты счета через CryptoBot API"""
    invoice_id = int(call.data.split("check_invoice:")[1])

    db_inv = await db.get_db_invoice(invoice_id)
    if db_inv and db_inv.get("status") == "paid":
        await call.answer("✅ Этот счет уже успешно оплачен и зачислен.", show_alert=True)
        return

    is_paid = await CryptoPayService.is_invoice_paid(invoice_id)
    if not is_paid:
        await call.answer("⚠️ Оплата пока не поступила. Попробуйте снова через несколько секунд после подтверждения платежа.", show_alert=True)
        return

    # Обрабатываем оплату
    res = await db.process_paid_invoice(invoice_id, bot=bot)
    if not res:
        await call.answer("✅ Счет уже обработан.", show_alert=True)
        return

    if res["type"] == "deposit":
        success_text = (
            f"🎉 <b>Оплата успешно подтверждена!</b>\n\n"
            f"💰 На ваш баланс зачислено <b>+{res['amount']} ₽</b>.\n"
            f"Текущий баланс: <b>{res['new_balance']} ₽</b>."
        )
        await call.message.edit_text(text=success_text, reply_markup=back_keyboard(back_target="menu_balance"))
        await call.answer("Баланс успешно пополнен!", show_alert=True)
    else:
        until_str = res['active_until'].strftime('%d.%m.%Y %H:%M') if hasattr(res['active_until'], 'strftime') else str(res['active_until'])
        success_text = (
            f"🎉 <b>Подписка успешно оплачена и активирована!</b>\n\n"
            f"• <b>Тариф:</b> Стандартный\n"
            f"• <b>Срок действия:</b> до <b>{until_str}</b>\n\n"
            f"🔑 <b>Ваш ключ подключения:</b>\n"
            f"<code>{html.escape(res['vpn_link'])}</code>\n\n"
            f"📖 <b>Инструкция:</b> скопируйте ключ и вставьте в клиент (V2rayN, V2Box, Happ)."
        )
        await call.message.edit_text(text=success_text, reply_markup=back_keyboard())
        await call.answer("Подписка успешно активирована!", show_alert=True)


@router.callback_query(F.data.startswith("check_fk_invoice:"))
async def cb_check_fk_invoice(call: CallbackQuery, bot: Bot):
    """Проверка статуса оплаты счета через FreeKassa REST API"""
    invoice_id = int(call.data.split("check_fk_invoice:")[1])

    db_inv = await db.get_db_invoice(invoice_id)
    if db_inv and db_inv.get("status") == "paid":
        await call.answer("✅ Этот счет уже успешно оплачен и зачислен.", show_alert=True)
        return

    # Проверяем через REST API FreeKassa
    is_paid = await FreeKassaService.is_order_paid(invoice_id)
    if not is_paid:
        await call.answer("⚠️ Оплата пока не поступила. Если вы только что оплатили, подождите несколько секунд и проверьте снова.", show_alert=True)
        return

    res = await db.process_paid_invoice(invoice_id, bot=bot)
    if not res:
        await call.answer("✅ Счет уже обработан.", show_alert=True)
        return

    if res["type"] == "deposit":
        success_text = (
            f"🎉 <b>Оплата успешно подтверждена!</b>\n\n"
            f"💰 На ваш баланс зачислено <b>+{res['amount']} ₽</b> через FreeKassa (Карты/СБП).\n"
            f"Текущий баланс: <b>{res['new_balance']} ₽</b>."
        )
        await call.message.edit_text(text=success_text, reply_markup=back_keyboard(back_target="menu_balance"))
        await call.answer("Баланс успешно пополнен!", show_alert=True)
    else:
        until_str = res['active_until'].strftime('%d.%m.%Y %H:%M') if hasattr(res['active_until'], 'strftime') else str(res['active_until'])
        success_text = (
            f"🎉 <b>Подписка успешно оплачена и активирована!</b>\n\n"
            f"• <b>Тариф:</b> Стандартный\n"
            f"• <b>Срок действия:</b> до <b>{until_str}</b>\n\n"
            f"🔑 <b>Ваш ключ подключения:</b>\n"
            f"<code>{html.escape(res['vpn_link'])}</code>\n\n"
            f"📖 <b>Инструкция:</b> скопируйте ключ и вставьте в клиент (V2rayN, V2Box, Happ)."
        )
        await call.message.edit_text(text=success_text, reply_markup=back_keyboard())
        await call.answer("Подписка успешно активирована!", show_alert=True)
