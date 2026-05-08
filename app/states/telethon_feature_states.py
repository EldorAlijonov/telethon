from aiogram.fsm.state import State, StatesGroup


class TelethonFeatureState(StatesGroup):
    waiting_keyword_add = State()
    waiting_keyword_edit_old = State()
    waiting_keyword_edit_new = State()
    waiting_keyword_delete = State()
