from aiogram.fsm.state import StatesGroup, State


class AddWishStates(StatesGroup):
    waiting_for_wish_text = State()
    waiting_for_description = State()
    waiting_for_priority = State()
    waiting_for_price = State()
    confirm_wish = State()


class ViewWishStates(StatesGroup):
    viewing_wishes = State()
    viewing_wish_detail = State()
    confirming_delete = State()
    viewing_other_wishes = State()
