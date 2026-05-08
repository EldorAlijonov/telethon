from aiogram.fsm.state import State, StatesGroup


class AdminActionState(StatesGroup):
    waiting_for_delete_user_id = State()
    waiting_for_approve_user_id = State()
