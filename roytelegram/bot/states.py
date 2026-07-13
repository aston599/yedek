from aiogram.fsm.state import State, StatesGroup


class AdminEdit(StatesGroup):
    waiting_value = State()
    waiting_image = State()
    waiting_profile_image = State()
    waiting_profile_cover = State()
    waiting_inline_button = State()
    waiting_menu_button = State()
    waiting_broadcast = State()
