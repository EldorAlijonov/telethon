from aiogram.fsm.state import State, StatesGroup


class AdminActionState(StatesGroup):
    waiting_for_approve_user_id = State()
    waiting_for_approve_access_days = State()
    waiting_for_block_user_id = State()
    waiting_for_delete_user_id = State()
    waiting_for_broadcast_text = State()
    waiting_for_stop_monitoring_user_id = State()
