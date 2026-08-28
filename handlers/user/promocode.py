import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database.db as db
from states.user_states import PromoStates
from keyboards.user_kb import cancel_state_keyboard, back_keyboard

router = Router()


@router.callback_query(F.data == "menu_promocode")
async def cb_promocode(call: CallbackQuery, state: FSMContext):
    """Запрос ввода промокода"""
    await state.set_state(PromoStates.waiting_code)
    text = (
        "🎫 <b>Активация промокода</b>\n\n"
        "Отправьте промокод в чат сообщением:"
    )
    await call.message.edit_text(text=text, reply_markup=cancel_state_keyboard(back_target="main_menu"))
    await call.answer()


@router.message(PromoStates.waiting_code)
async def process_promocode(message: Message, state: FSMContext):
    """Обработка введенного промокода"""
    code = message.text.strip()
    user_id = message.from_user.id

    result = await db.activate_promocode(code, user_id)
    await state.clear()

    if result["success"]:
        text = (
            f"🎉 <b>Промокод «{html.escape(code)}» успешно активирован!</b>\n\n"
            f"🎁 Вам начислено: <b>{result['reward_desc']}</b>"
        )
    else:
        text = (
            f"❌ <b>Не удалось активировать промокод.</b>\n\n"
            f"{result.get('msg', 'Неверный промокод.')}"
        )

    await message.answer(text=text, reply_markup=back_keyboard())
