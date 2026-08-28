from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_password = State()
    waiting_new_price = State()
    waiting_ticket_reply = State()
    waiting_add_admin_id = State()
    waiting_promocode_data = State()
    waiting_broadcast_text = State()
