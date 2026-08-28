import html
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

import config
import database.db as db
from services.qr_service import QRService
from keyboards.user_kb import partner_keyboard, back_keyboard

router = Router()


def get_partner_text(bot_username: str, user_id: int, stats: dict) -> str:
    ref_code = f"ref{user_id}"
    ref_link = f"https://t.me/{bot_username}?start={ref_code}"

    return (
        f"👥 <b>Реферальная программа</b>\n\n"
        f"📊 <b>Ваша статистика:</b>\n"
        f"• Приглашено пользователей: {stats['total_invited']}\n"
        f"• Сделали первое пополнение: {stats['first_deposits']}\n"
        f"• Активных рефералов: {stats['active_referrals']}\n"
        f"• Конверсия: {stats['conversion']}%\n"
        f"• Заработано всего: {stats['total_earned']} ₽\n"
        f"• За последний месяц: {stats['month_earned']} ₽\n\n"
        f"🎁 <b>Как работают награды:</b>\n"
        f"• Вы получаете при первом пополнении реферала: {config.REFERRAL_BONUS_RUB} ₽\n"
        f"• Комиссия с каждого пополнения реферала: {config.REFERRAL_PERCENT}%\n\n"
        f"🤖 <b>Ссылка на бота:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"🆔 <b>Ваш код:</b> <code>{ref_code}</code>\n\n"
        f"📢 <b>Приглашайте друзей и зарабатывайте!</b>"
    )


@router.callback_query(F.data == "menu_partner")
async def cb_partner(call: CallbackQuery, bot: Bot):
    """Экран реферальной программы"""
    bot_info = await bot.get_me()
    bot_username = bot_info.username or config.BOT_USERNAME or "bot"
    stats = await db.get_referral_stats(call.from_user.id)

    text = get_partner_text(bot_username, call.from_user.id, stats)
    await call.message.edit_text(
        text=text,
        reply_markup=partner_keyboard(),
        disable_web_page_preview=True
    )
    await call.answer()


@router.callback_query(F.data == "partner_invite")
async def cb_partner_invite(call: CallbackQuery, bot: Bot):
    """Готовое сообщение для отправки друзьям"""
    bot_info = await bot.get_me()
    bot_username = bot_info.username or config.BOT_USERNAME or "bot"
    ref_link = f"https://t.me/{bot_username}?start=ref{call.from_user.id}"

    text = (
        "📝 <b>Текст для приглашения друзей:</b>\n\n"
        "Скопируйте и перешлите следующее сообщение другу:\n\n"
        f"<blockquote>🛡 Пользуйся быстрым и надежным VPN без ограничений скорости!\n"
        f"Переходи по ссылке и получай бонусные дни: {ref_link}</blockquote>"
    )
    await call.message.edit_text(text=text, reply_markup=back_keyboard(back_target="menu_partner"))
    await call.answer()


@router.callback_query(F.data == "partner_qr")
async def cb_partner_qr(call: CallbackQuery, bot: Bot):
    """Генерация и отправка QR-кода реферальной ссылки"""
    bot_info = await bot.get_me()
    bot_username = bot_info.username or config.BOT_USERNAME or "bot"
    ref_link = f"https://t.me/{bot_username}?start=ref{call.from_user.id}"
    qr_url = QRService.get_qr_url(ref_link)

    text = (
        f"📱 <b>QR-код вашей реферальной ссылки:</b>\n\n"
        f"<code>{ref_link}</code>\n\n"
        f"Покажите этот QR-код друзьям для быстрого сканирования камерой телефона."
    )
    try:
        await call.message.delete()
        await call.message.answer_photo(
            photo=qr_url,
            caption=text,
            reply_markup=back_keyboard(back_target="menu_partner")
        )
    except Exception:
        await call.message.edit_text(text=text, reply_markup=back_keyboard(back_target="menu_partner"))
    await call.answer()


@router.callback_query(F.data == "partner_list")
async def cb_partner_list(call: CallbackQuery):
    """Список приглашенных рефералов"""
    referrals = await db.get_referral_list(call.from_user.id)
    if not referrals:
        text = "👥 <b>Список рефералов:</b>\n\nУ вас пока нет приглашенных пользователей."
    else:
        text = f"👥 <b>Ваши рефералы ({len(referrals)}):</b>\n\n"
        for i, ref in enumerate(referrals, 1):
            uname = f"@{ref['username']}" if ref['username'] else ref['full_name']
            text += f"{i}. {html.escape(uname)} (доход: {ref['total_earned']} ₽)\n"

    await call.message.edit_text(text=text, reply_markup=back_keyboard(back_target="menu_partner"))
    await call.answer()


@router.callback_query(F.data == "partner_analytics")
async def cb_partner_analytics(call: CallbackQuery):
    """Подробная аналитика партнерской программы"""
    stats = await db.get_referral_stats(call.from_user.id)
    text = (
        "📊 <b>Детальная аналитика:</b>\n\n"
        f"• Всего переходов по ссылке: <b>{stats['total_invited']}</b>\n"
        f"• Оплативших пользователей: <b>{stats['first_deposits']}</b>\n"
        f"• Конверсия в оплату: <b>{stats['conversion']}%</b>\n"
        f"• Доход за всё время: <b>{stats['total_earned']} ₽</b>\n"
        f"• Доход за последние 30 дней: <b>{stats['month_earned']} ₽</b>"
    )
    await call.message.edit_text(text=text, reply_markup=back_keyboard(back_target="menu_partner"))
    await call.answer()
