import html
import logging
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext

import config
import database.db as db
from keyboards.user_kb import main_keyboard, info_menu_keyboard, back_keyboard, channel_subscription_keyboard

logger = logging.getLogger(__name__)
router = Router()


async def is_subscribed_to_channel(bot: Bot, user_id: int) -> bool:
    """Проверка, подписан ли пользователь на обязательный канал"""
    channel = getattr(config, "REQUIRED_CHANNEL", "")
    if not channel:
        return True
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        if member.status in ["member", "administrator", "creator", "restricted"]:
            return True
        return False
    except Exception as e:
        logger.warning(f"Проверка подписки на {channel} для {user_id}: {e}")
        # Если бот не админ в канале или произошла ошибка доступа, не блокируем бота
        return True


def format_sub_status(user: dict) -> str:
    """Форматирование статуса подписки для главного экрана"""
    if not user:
        return "❌ Отсутствует"

    until_str = user.get("sub_active_until")
    if not until_str:
        return "❌ Отсутствует"

    try:
        until_dt = datetime.fromisoformat(until_str)
        if until_dt > datetime.now():
            plan = user.get("sub_plan") or "Активна"
            return f"✅ {plan} (до {until_dt.strftime('%d.%m.%Y %H:%M')})"
    except Exception:
        pass

    return "❌ Отсутствует"


def get_main_text(user_full_name: str, sub_status: str) -> str:
    return (
        f"👤 <b>{html.escape(user_full_name)}</b>\n\n"
        f"📱 Подписка: {sub_status}\n\n"
        f"Выберите действие:"
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject, bot: Bot):
    """Обработка команды /start с реферальной системой"""
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or "Пользователь"

    # Создаем или обновляем пользователя
    user = await db.get_or_create_user(user_id, username, full_name)

    # Обработка реферального кода
    args = command.args if command else None
    if args and args.startswith("ref"):
        try:
            ref_raw = args.replace("ref", "").strip()
            if ref_raw.isdigit():
                referrer_id = int(ref_raw)
                is_set = await db.set_referrer(user_id, referrer_id)
                if is_set:
                    try:
                        await bot.send_message(
                            chat_id=referrer_id,
                            text=(
                                f"🎉 <b>По вашей реферальной ссылке зарегистрировался новый пользователь!</b>\n\n"
                                f"👤 {html.escape(full_name)} (@{html.escape(username)})"
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Не удалось отправить уведомление рефереру {referrer_id}: {e}")
        except Exception as e:
            logger.error(f"Ошибка при обработке реферального кода: {e}")

    # Проверка обязательной подписки на канал
    is_sub = await is_subscribed_to_channel(bot, user_id)
    if not is_sub:
        channel_name = getattr(config, 'REQUIRED_CHANNEL', '@Ershvpn')
        welcome_sub_text = (
            f"👋 <b>Добро пожаловать в Ersh VPN, {html.escape(full_name)}!</b>\n\n"
            f"📢 Для использования бота необходимо подписаться на наш официальный Telegram-канал:\n"
            f"<b>{channel_name}</b>\n\n"
            f"1. Нажмите кнопку <b>«📢 Подписаться на канал»</b> ниже.\n"
            f"2. После подписки нажмите <b>«🔄 Я подписался / Проверить»</b>."
        )
        await message.answer(
            text=welcome_sub_text,
            reply_markup=channel_subscription_keyboard()
        )
        return

    sub_status = format_sub_status(user)
    has_active = "✅" in sub_status

    # Устанавливаем постоянную кнопку "Cabinet" в интерфейсе чата
    if getattr(config, 'WEBAPP_URL', ''):
        try:
            from aiogram.types import MenuButtonWebApp, WebAppInfo
            await bot.set_chat_menu_button(
                chat_id=user_id,
                menu_button=MenuButtonWebApp(
                    text="Cabinet",
                    web_app=WebAppInfo(url=f"{config.WEBAPP_URL.rstrip('/')}/webapp/index.html")
                )
            )
        except Exception:
            pass

    await message.answer(
        text=get_main_text(full_name, sub_status),
        reply_markup=main_keyboard(balance=user.get("balance", 0), has_active_sub=has_active)
    )


@router.callback_query(F.data == "check_channel_sub")
async def cb_check_channel_sub(call: CallbackQuery, bot: Bot, state: FSMContext):
    """Проверка обязательной подписки по кнопке"""
    user_id = call.from_user.id
    is_sub = await is_subscribed_to_channel(bot, user_id)
    if not is_sub:
        channel_name = getattr(config, 'REQUIRED_CHANNEL', '@Ershvpn')
        await call.answer(f"❌ Вы еще не подписались на канал {channel_name}! Пожалуйста, подпишитесь для продолжения.", show_alert=True)
        return

    await call.answer("✅ Подписка подтверждена! Добро пожаловать.")
    user = await db.get_or_create_user(user_id, call.from_user.username or "", call.from_user.full_name or "Пользователь")
    sub_status = format_sub_status(user)
    has_active = "✅" in sub_status

    if getattr(config, 'WEBAPP_URL', ''):
        try:
            from aiogram.types import MenuButtonWebApp, WebAppInfo
            await bot.set_chat_menu_button(
                chat_id=user_id,
                menu_button=MenuButtonWebApp(
                    text="Cabinet",
                    web_app=WebAppInfo(url=f"{config.WEBAPP_URL.rstrip('/')}/webapp/index.html")
                )
            )
        except Exception:
            pass

    await call.message.edit_text(
        text=get_main_text(call.from_user.full_name or "Пользователь", sub_status),
        reply_markup=main_keyboard(balance=user.get("balance", 0), has_active_sub=has_active)
    )


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(call: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    user = await db.get_user(call.from_user.id)
    name = call.from_user.full_name or "Пользователь"
    sub_status = format_sub_status(user)
    has_active = "✅" in sub_status

    await call.message.edit_text(
        text=get_main_text(name, sub_status),
        reply_markup=main_keyboard(balance=user.get("balance", 0) if user else 0, has_active_sub=has_active)
    )
    await call.answer()


@router.callback_query(F.data.startswith("cancel_to:"))
async def cb_cancel_state(call: CallbackQuery, state: FSMContext):
    """Отмена текущего ввода и возврат к целевому меню"""
    await state.clear()
    target = call.data.split("cancel_to:")[1]
    if target == "main_menu":
        user = await db.get_user(call.from_user.id)
        name = call.from_user.full_name or "Пользователь"
        sub_status = format_sub_status(user)
        has_active = "✅" in sub_status
        await call.message.edit_text(
            text=get_main_text(name, sub_status),
            reply_markup=main_keyboard(balance=user.get("balance", 0) if user else 0, has_active_sub=has_active)
        )
    else:
        await call.message.edit_text("Действие отменено.", reply_markup=back_keyboard(target))
    await call.answer()


@router.callback_query(F.data == "menu_info")
async def cb_info(call: CallbackQuery):
    """Раздел: Инфо о сервисе и юридическая информация"""
    text = (
        "ℹ️ <b>О нашем сервисе VPN</b>\n\n"
        "⚡ <b>Высокая скорость:</b> Серверы со скоростью до 1 Гбит/с без ограничений по трафику.\n"
        "🛡 <b>Надежная защита:</b> Современный протокол VLESS Reality (маскировка под веб-трафик).\n"
        "📱 <b>Любые устройства:</b> iOS, Android, Windows, macOS, Linux.\n"
        "🚫 <b>Без логов:</b> Мы не ведем логи активности и уважаем вашу конфиденциальность.\n\n"
        "📖 <b>Правовая информация:</b>\n"
        "Ознакомьтесь с условиями предоставления услуг и политикой конфиденциальности по кнопкам ниже:"
    )
    await call.message.edit_text(text=text, reply_markup=info_menu_keyboard())
    await call.answer()


@router.callback_query(F.data == "info_terms")
async def cb_info_terms(call: CallbackQuery):
    """Пользовательское соглашение"""
    text = (
        "📄 <b>Пользовательское соглашение</b>\n\n"
        "<blockquote>Используя Сервис (в том числе запуская бота и/или вводя команду /start), "
        "Пользователь подтверждает, что ознакомлен с настоящим Соглашением и принимает его условия в полном объёме.</blockquote>\n\n"
        "<b>1. Общие положения</b>\n"
        "1.1. Настоящее Соглашение регулирует порядок использования онлайн-сервиса (далее — «Сервис»).\n"
        "1.2. Используя Сервис, Пользователь подтверждает, что полностью ознакомился с условиями и принимает их.\n"
        "1.3. В случае несогласия Пользователь обязан прекратить использование Сервиса.\n\n"
        "<b>2. Характер услуг и цифровых товаров</b>\n"
        "2.1. Сервис предоставляет цифровые услуги нематериального характера (VPN-доступ, сопровождение и поддержка).\n"
        "2.2. Сервис предоставляется на условиях «AS IS» («как есть»).\n\n"
        "<b>3. Законность и ответственность</b>\n"
        "3.1. Сервис не предназначен для поощрения противоправной деятельности.\n"
        "3.2. Ответственность за законность использования возлагается на Пользователя.\n\n"
        "<b>4. Платежи и возвраты</b>\n"
        "4.1. В связи с нематериальным характером услуг, возврат средств после предоставления доступа не осуществляется, "
        "за исключением случаев, когда услуга не была оказана по технической вине Сервиса.\n"
        "4.2. Для рассмотрения возврата Пользователь обязан обратиться в поддержку бота в течение 24 часов с момента оплаты.\n"
        "4.3. Пользователь обязуется не инициировать chargeback без предварительного обращения в службу поддержки.\n\n"
        "<b>5. Контакты и поддержка</b>\n"
        "5.1. Все вопросы и обращения принимаются через службу поддержки в боте (/start → Техподдержка)."
    )
    await call.message.edit_text(text=text, reply_markup=back_keyboard(back_target="menu_info"))
    await call.answer()


@router.callback_query(F.data == "info_privacy")
async def cb_info_privacy(call: CallbackQuery):
    """Политика конфиденциальности"""
    text = (
        "🔒 <b>Политика конфиденциальности</b>\n\n"
        "<b>1. Общие положения</b>\n"
        "1.1. Настоящая Политика регулирует порядок обработки и защиты информации при использовании Сервиса.\n"
        "1.2. Используя Сервис, Пользователь подтверждает согласие с Политикой.\n\n"
        "<b>2. Сбор информации</b>\n"
        "2.1. Сервис обрабатывает технические идентификаторы аккаунта (Telegram ID, username) для работы подписки.\n"
        "2.2. Сервис <b>не требует</b> предоставления паспортных данных, документов или личных фотографий.\n\n"
        "<b>3. Использование и защита данных</b>\n"
        "3.1. Данные используются исключительно для обеспечения работы VPN, начисления бонусов и поддержки.\n"
        "3.2. Администрация не передаёт данные третьим лицам, за исключением случаев, установленных законом или необходимых для проведения платежей через платёжные шлюзы.\n"
        "3.3. Применяются современные технические меры защиты информации."
    )
    await call.message.edit_text(text=text, reply_markup=back_keyboard(back_target="menu_info"))
    await call.answer()


@router.callback_query(F.data == "my_vpn_key")
async def cb_my_vpn(call: CallbackQuery):
    """Отображение текущего ключа подключения"""
    user = await db.get_user(call.from_user.id)
    vpn_key = user.get("vpn_key") if user else None

    if not vpn_key:
        await call.message.edit_text(
            "❌ У вас пока нет активного ключа подключения. Оформите тестовый период или подписку.",
            reply_markup=back_keyboard()
        )
        await call.answer()
        return

    text = (
        f"🔑 <b>Ваш ключ подключения:</b>\n\n"
        f"<code>{html.escape(vpn_key)}</code>\n\n"
        f"📖 <b>Инструкция по подключению:</b>\n"
        f"1. Скопируйте ключ выше (нажатием на него).\n"
        f"2. Скачайте приложение для вашей системы (<b>V2rayN</b> на Windows, <b>V2Box / Happ</b> на iOS/Android).\n"
        f"3. Добавьте конфигурацию из буфера обмена и нажмите «Подключиться»."
    )
    await call.message.edit_text(text=text, reply_markup=back_keyboard())
    await call.answer()
