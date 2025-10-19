from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext

import db_controller
from states import *

router = Router()

# ============== Start Command ==============
@router.message(Command(commands=["start"]))
async def start(message: Message):
    # Добавляем пользователя в БД если его еще нет
    user_exists = db_controller.user_exists(message.from_user.id)
    if not user_exists:
        db_controller.add_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
    
    main_menu = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Добавить желание", callback_data="add_wish_start")],
        [InlineKeyboardButton(text="📋 Посмотреть мои желания", callback_data="show_my_wishes")]
    ])
    await message.answer("Добро пожаловать в WishList! 🎉", reply_markup=main_menu)


# ============== Get User Wishes Command ==============
@router.message(Command(commands=["wish_list"]))
async def get_wish_list(message: Message, state: FSMContext):
    """Получить список желаний пользователя (работает в группах и личке)"""
    # Извлекаем username из аргументов команды
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer("❌ Использование: /wish_list @username")
        return
    
    username = args[1]
    
    # Ищем пользователя по username
    target_user = db_controller.get_user_by_username(username)
    
    if not target_user:
        await message.answer(f"❌ Пользователь {username} не найден 😔")
        return
    
    # Получаем желания пользователя
    wishes = db_controller.get_user_wishes(target_user['user_id'])
    
    if not wishes:
        await message.answer(
            f"📋 У пользователя {username} еще нет желаний 😔"
        )
        return
    
    # Отправляем в приватный чат
    try:
        # Отправляем сообщение в личку
        sent_message = await message.bot.send_message(
            chat_id=message.from_user.id,
            text="📋 <b>Желания:</b>",
            parse_mode="HTML"
        )
        
        # Сохраняем данные в состояние и показываем список
        await state.update_data(
            wishes_list=wishes, 
            current_page=0, 
            is_owner=False,
            target_username=username
        )
        await state.set_state(ViewWishStates.viewing_other_wishes)
        
        # Создаём callback-объект для show_wishes_page_other
        class FakeCallback:
            def __init__(self, msg):
                self.message = msg
                self.from_user = message.from_user
            async def answer(self):
                pass
        
        fake_callback = FakeCallback(sent_message)
        await show_wishes_page_other(fake_callback, state, 0, username)
        
        # Ответ в группе
        await message.reply(
            f"✅ Список желаний пользователя {username} отправлен в личку 📬"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке: {str(e)}")


# ============== Add Wish Flow ==============
@router.callback_query(F.data == "add_wish_start")
async def add_wish_start(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления желания"""
    await state.set_state(AddWishStates.waiting_for_wish_text)
    await callback.message.edit_text(
        "✍️ Напишите, что вы хотите добавить в список желаний:"
    )
    await callback.answer()


@router.message(AddWishStates.waiting_for_wish_text)
async def wish_text_received(message: Message, state: FSMContext):
    """Получение текста желания"""
    if not message.text or len(message.text) < 3:
        await message.answer("❌ Текст желания должен содержать минимум 3 символа. Попробуйте снова:")
        return
    
    await state.update_data(wish_text=message.text)
    await state.set_state(AddWishStates.waiting_for_description)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="skip_description")]
    ])
    await message.answer(
        f"✅ Записал: \"{message.text}\"\n\n"
        "📝 Добавьте описание (опционально) или нажмите 'Пропустить':",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "skip_description", AddWishStates.waiting_for_description)
async def skip_description(callback: CallbackQuery, state: FSMContext):
    """Пропустить описание"""
    await state.update_data(description=None)
    await state.set_state(AddWishStates.waiting_for_priority)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1⭐", callback_data="priority_1"),
         InlineKeyboardButton(text="2⭐", callback_data="priority_2"),
         InlineKeyboardButton(text="3⭐", callback_data="priority_3")],
        [InlineKeyboardButton(text="4⭐", callback_data="priority_4"),
         InlineKeyboardButton(text="5⭐", callback_data="priority_5")]
    ])
    await callback.message.edit_text(
        "⭐ Выберите приоритет желания (1 = низкий, 5 = высокий):",
        reply_markup=keyboard
    )
    await callback.answer()


@router.message(AddWishStates.waiting_for_description)
async def description_received(message: Message, state: FSMContext):
    """Получение описания желания"""
    if message.text:
        await state.update_data(description=message.text)
    
    await state.set_state(AddWishStates.waiting_for_priority)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1⭐", callback_data="priority_1"),
         InlineKeyboardButton(text="2⭐", callback_data="priority_2"),
         InlineKeyboardButton(text="3⭐", callback_data="priority_3")],
        [InlineKeyboardButton(text="4⭐", callback_data="priority_4"),
         InlineKeyboardButton(text="5⭐", callback_data="priority_5")]
    ])
    await message.answer(
        "⭐ Выберите приоритет желания (1 = низкий, 5 = высокий):",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("priority_"), AddWishStates.waiting_for_priority)
async def priority_selected(callback: CallbackQuery, state: FSMContext):
    """Выбор приоритета"""
    priority = int(callback.data.split("_")[1])
    await state.update_data(priority=priority)
    await state.set_state(AddWishStates.waiting_for_price)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="skip_price")]
    ])
    await callback.message.edit_text(
        f"✅ Приоритет установлен на {priority}⭐\n\n"
        "💰 Укажите стоимость в рублях (опционально) или нажмите 'Пропустить':",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "skip_price", AddWishStates.waiting_for_price)
async def skip_price(callback: CallbackQuery, state: FSMContext):
    """Пропустить цену"""
    await state.update_data(price=None)
    await confirm_wish_data(callback, state)


@router.message(AddWishStates.waiting_for_price)
async def price_received(message: Message, state: FSMContext):
    """Получение цены"""
    try:
        price = float(message.text)
        if price < 0:
            await message.answer("❌ Цена не может быть отрицательной. Попробуйте снова:")
            return
        await state.update_data(price=price)
    except ValueError:
        await message.answer("❌ Введите корректную цену (число). Попробуйте снова:")
        return
    
    await confirm_wish_data(message, state)


async def confirm_wish_data(obj: Message | CallbackQuery, state: FSMContext):
    """Подтверждение данных желания"""
    data = await state.get_data()
    
    wish_text = data.get("wish_text")
    description = data.get("description", "Не указано")
    priority = data.get("priority", 3)
    price = data.get("price")
    price_text = f"₽{price:.2f}" if price else "Не указано"
    
    confirmation_text = (
        f"📋 Проверьте данные желания:\n\n"
        f"🎁 Желание: {wish_text}\n"
        f"📝 Описание: {description}\n"
        f"⭐ Приоритет: {priority}\n"
        f"💰 Стоимость: {price_text}\n\n"
        f"Все правильно?"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сохранить", callback_data="confirm_save_wish"),
         InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_wish")]
    ])
    
    if isinstance(obj, CallbackQuery):
        await obj.message.edit_text(confirmation_text, reply_markup=keyboard)
        await obj.answer()
    else:
        await obj.answer(confirmation_text, reply_markup=keyboard)
    
    await state.set_state(AddWishStates.confirm_wish)


@router.callback_query(F.data == "confirm_save_wish", AddWishStates.confirm_wish)
async def save_wish(callback: CallbackQuery, state: FSMContext):
    """Сохранение желания в БД"""
    data = await state.get_data()
    
    try:
        wish_id = db_controller.add_wish(
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            wish_text=data["wish_text"],
            description=data.get("description"),
            priority=data.get("priority", 3),
            price=data.get("price")
        )
        
        if wish_id:
            await callback.message.edit_text(
                f"✅ Желание успешно добавлено! (ID: {wish_id})\n\n"
                "Вы можете добавить еще одно желание или вернуться в главное меню."
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить еще", callback_data="add_wish_start")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        else:
            await callback.message.edit_text("❌ Ошибка при сохранении желания. Попробуйте снова.")
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_wish")
async def cancel_wish(callback: CallbackQuery, state: FSMContext):
    """Отмена добавления желания"""
    await state.clear()
    
    main_menu = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Добавить желание", callback_data="add_wish_start")],
        [InlineKeyboardButton(text="📋 Посмотреть мои желания", callback_data="show_my_wishes")]
    ])
    await callback.message.edit_text("❌ Добавление желания отменено.\n\nЧто вы хотите сделать?", reply_markup=main_menu)
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    
    main_menu_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Добавить желание", callback_data="add_wish_start")],
        [InlineKeyboardButton(text="📋 Посмотреть мои желания", callback_data="show_my_wishes")]
    ])
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu_kb)
    await callback.answer()


# ============== View Wishes Flow ==============
WISHES_PER_PAGE = 5

@router.callback_query(F.data == "show_my_wishes")
async def show_my_wishes(callback: CallbackQuery, state: FSMContext):
    """Показать все желания пользователя"""
    user_id = callback.from_user.id
    wishes = db_controller.get_user_wishes(user_id)
    
    if not wishes:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Добавить желание", callback_data="add_wish_start")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await callback.message.edit_text(
            "📋 У вас еще нет желаний.\n\n"
            "Создайте первое желание и оно появится здесь!",
            reply_markup=keyboard
        )
        await callback.answer()
        return
    
    # Сохраняем список желаний и показываем первую страницу
    await state.update_data(wishes_list=wishes, current_page=0, is_owner=True)
    await state.set_state(ViewWishStates.viewing_wishes)
    await show_wishes_page(callback, state, 0, is_owner=True)


async def show_wishes_page(callback: CallbackQuery, state: FSMContext, page: int, is_owner: bool = True):
    """Показать страницу со списком желаний. is_owner=True показывает кнопки удаления"""
    data = await state.get_data()
    wishes = data.get("wishes_list", [])
    
    if not wishes:
        return
    
    # Вычисляем индексы для этой страницы
    start_idx = page * WISHES_PER_PAGE
    end_idx = start_idx + WISHES_PER_PAGE
    page_wishes = wishes[start_idx:end_idx]
    total_pages = (len(wishes) + WISHES_PER_PAGE - 1) // WISHES_PER_PAGE
    
    # Формируем список желаний
    title = "📋 <b>Ваши желания:</b>\n\n" if is_owner else "📋 <b>Желания:</b>\n\n"
    wishes_text = title
    for idx, wish in enumerate(page_wishes, 1):
        wish_number = start_idx + idx
        priority_stars = "⭐" * wish["priority"]
        price_text = f"₽{wish['price']:.2f}" if wish["price"] else "—"
        
        wishes_text += (
            f"{wish_number}. <b>{wish['wish_text']}</b>\n"
            f"   🌟 {priority_stars} | 💰 {price_text} | 📅 {wish['status']}\n"
        )
        if wish["description"]:
            # Обрезаем длинное описание
            desc = wish["description"][:40] + "..." if len(wish["description"]) > 40 else wish["description"]
            wishes_text += f"   📝 {desc}\n"
        wishes_text += "\n"
    
    # Кнопки удаления (только для владельца)
    keyboard_buttons = []
    if is_owner:
        for idx, wish in enumerate(page_wishes):
            wish_number = start_idx + idx + 1
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"🗑️ Удалить #{wish_number}", callback_data=f"wish_delete_{wish['wish_id']}")
            ])
    
    # Кнопки навигации между страницами
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_wishes_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Далее ➡️", callback_data=f"page_wishes_{page + 1}"))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    # Главное меню
    keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    
    # Добавляем информацию о странице если страниц больше одной
    if total_pages > 1:
        wishes_text += f"\n📄 Страница {page + 1} из {total_pages}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(wishes_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


async def show_wishes_page_other(callback: CallbackQuery, state: FSMContext, page: int, username: str):
    """Показать страницу со списком желаний другого пользователя (без кнопок удаления)"""
    data = await state.get_data()
    wishes = data.get("wishes_list", [])
    
    if not wishes:
        return
    
    # Вычисляем индексы для этой страницы
    start_idx = page * WISHES_PER_PAGE
    end_idx = start_idx + WISHES_PER_PAGE
    page_wishes = wishes[start_idx:end_idx]
    total_pages = (len(wishes) + WISHES_PER_PAGE - 1) // WISHES_PER_PAGE
    
    # Формируем список желаний
    wishes_text = f"📋 <b>Желания пользователя {username}:</b>\n\n"
    for idx, wish in enumerate(page_wishes, 1):
        wish_number = start_idx + idx
        priority_stars = "⭐" * wish["priority"]
        price_text = f"₽{wish['price']:.2f}" if wish["price"] else "—"
        
        wishes_text += (
            f"{wish_number}. <b>{wish['wish_text']}</b>\n"
            f"   🌟 {priority_stars} | 💰 {price_text} | 📅 {wish['status']}\n"
        )
        if wish["description"]:
            # Обрезаем длинное описание
            desc = wish["description"][:40] + "..." if len(wish["description"]) > 40 else wish["description"]
            wishes_text += f"   📝 {desc}\n"
        wishes_text += "\n"
    
    # Кнопки навигации между страницами (без кнопок удаления)
    keyboard_buttons = []
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_other_wishes_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Далее ➡️", callback_data=f"page_other_wishes_{page + 1}"))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    # Главное меню
    keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    
    # Добавляем информацию о странице если страниц больше одной
    if total_pages > 1:
        wishes_text += f"\n📄 Страница {page + 1} из {total_pages}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(wishes_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("page_other_wishes_"), ViewWishStates.viewing_other_wishes)
async def page_other_wishes(callback: CallbackQuery, state: FSMContext):
    """Переключиться между страницами желаний другого пользователя"""
    page = int(callback.data.split("_")[3])
    data = await state.get_data()
    username = data.get("target_username")
    await state.update_data(current_page=page)
    await show_wishes_page_other(callback, state, page, username)


@router.callback_query(F.data.startswith("page_wishes_"), ViewWishStates.viewing_wishes)
async def page_wishes(callback: CallbackQuery, state: FSMContext):
    """Переключиться между страницами желаний"""
    page = int(callback.data.split("_")[2])
    data = await state.get_data()
    is_owner = data.get("is_owner", True)
    await state.update_data(current_page=page)
    await show_wishes_page(callback, state, page, is_owner=is_owner)


@router.callback_query(F.data.startswith("wish_delete_"), ViewWishStates.viewing_wishes)
async def wish_delete_confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждение удаления желания"""
    wish_id = int(callback.data.split("_")[2])
    wish = db_controller.get_wish(wish_id)
    
    if not wish:
        await callback.answer("❌ Желание не найдено", show_alert=True)
        return
    
    await state.update_data(wish_to_delete=wish_id)
    await state.set_state(ViewWishStates.confirming_delete)
    
    confirm_text = (
        f"⚠️ <b>Вы уверены, что хотите удалить это желание?</b>\n\n"
        f"🎁 <b>{wish['wish_text']}</b>\n\n"
        f"Это действие нельзя отменить!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete_wish"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete_wish")]
    ])
    
    await callback.message.edit_text(confirm_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "confirm_delete_wish", ViewWishStates.confirming_delete)
async def confirm_delete_wish(callback: CallbackQuery, state: FSMContext):
    """Удалить желание"""
    data = await state.get_data()
    wish_id = data.get("wish_to_delete")
    
    if db_controller.delete_wish(wish_id):
        await callback.answer("✅ Желание удалено!", show_alert=False)
        
        # Обновляем список желаний
        user_id = callback.from_user.id
        remaining_wishes = db_controller.get_user_wishes(user_id)
        
        if remaining_wishes:
            # Проверяем, нужно ли переходить на предыдущую страницу
            current_page = data.get("current_page", 0)
            total_pages = (len(remaining_wishes) + WISHES_PER_PAGE - 1) // WISHES_PER_PAGE
            
            if current_page >= total_pages:
                current_page = total_pages - 1
            
            await state.update_data(wishes_list=remaining_wishes, current_page=current_page)
            await state.set_state(ViewWishStates.viewing_wishes)
            await show_wishes_page(callback, state, current_page)
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎁 Добавить желание", callback_data="add_wish_start")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            await callback.message.edit_text(
                "📋 У вас больше нет желаний.",
                reply_markup=keyboard
            )
            await state.clear()
    else:
        await callback.answer("❌ Ошибка при удалении желания", show_alert=True)


@router.callback_query(F.data == "cancel_delete_wish", ViewWishStates.confirming_delete)
async def cancel_delete_wish(callback: CallbackQuery, state: FSMContext):
    """Отмена удаления желания"""
    data = await state.get_data()
    current_page = data.get("current_page", 0)
    
    await state.set_state(ViewWishStates.viewing_wishes)
    await show_wishes_page(callback, state, current_page)


