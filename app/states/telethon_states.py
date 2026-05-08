from aiogram.fsm.state import State, StatesGroup


class TelethonState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_password = State()
