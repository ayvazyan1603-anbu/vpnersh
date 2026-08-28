from aiogram.fsm.state import State, StatesGroup

class PromoStates(StatesGroup):
    waiting_code = State()

class TicketStates(StatesGroup):
    waiting_text = State()

class DepositStates(StatesGroup):
    waiting_custom_amount = State()
