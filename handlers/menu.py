from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from database.database import get_session
from services.user_service import get_or_create_user
from services.office_service import get_all_offices
from services.cafe_service import get_all_cafes, get_cafe_menu_for_date
from services.cafe_service import get_cafe_by_id
from services.deadline_service import get_deadline_for_date
from utils.formatters import format_date
from utils.validators import validate_order_date
from config.settings import settings
from models.order import DeliveryType

router = Router()

class OrderStates(StatesGroup):
    choosing_office = State()
    choosing_cafe = State()
    choosing_date = State()
    choosing_dish = State()
    choosing_quantity = State()
    choosing_delivery = State()
    editing_cart_item = State()
    confirming_order = State()

@router.message(Command("menu"))
async def cmd_menu(message: Message):
    from utils.keyboards import get_back_keyboard
    await message.answer(
        "Используйте кнопку 'Создать заказ' из главного меню или команду /start",
        reply_markup=get_back_keyboard()
    )

@router.callback_query(lambda c: c.data == "create_order")
async def callback_create_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    saved_order_date = data.get("order_date")
    
    async for session in get_session():
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.full_name
        )
        
        if user.office_id:
            await state.update_data(office_id=user.office_id)
            cafes = await get_all_cafes(session, office_id=user.office_id)
            
            if not cafes:
                await callback.message.edit_text(
                    "⚠️ <b>Кафе недоступны</b>\n\n"
                    "Для вашего офиса пока нет доступных кафе.\n"
                    "Обратитесь к офис-менеджеру.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                    ]),
                    parse_mode="HTML"
                )
                await callback.answer()
                return
            
            keyboard_buttons = []
            for cafe in cafes:
                keyboard_buttons.append([InlineKeyboardButton(
                    text=f"☕ {cafe.name}",
                    callback_data=f"select_cafe_{cafe.id}"
                )])
            
            if cart and saved_order_date:
                total = sum(item["price"] * item["quantity"] for item in cart)
                keyboard_buttons.insert(0, [
                    InlineKeyboardButton(
                        text=f"🛒 Вернуться к корзине ({len(cart)} шт., {total:.0f} ₽)",
                        callback_data="return_to_cart"
                    )
                ])
            
            keyboard_buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
            keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
            
            text = "☕ <b>Выберите кафе</b>\n\n"
            text += "💡 Выберите кафе для заказа обеда"
            
            if cart and saved_order_date:
                text += f"\n\n🛒 У вас есть незавершенная корзина на <b>{format_date(saved_order_date)}</b>"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
                parse_mode="HTML"
            )
            await state.set_state(OrderStates.choosing_cafe)
        else:
            offices = await get_all_offices(session)
            
            if not offices:
                await callback.message.edit_text(
                    "\n"
                    "   ⚠️ <b>Офисы недоступны</b>\n"
                    "\n\n"
                    "Пока нет доступных офисов.\n"
                    "Обратитесь к офис-менеджеру.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                    ]),
                    parse_mode="HTML"
                )
                await callback.answer()
                return
            
            keyboard_buttons = []
            for office in offices:
                keyboard_buttons.append([InlineKeyboardButton(
                    text=f"🏢 {office.name}",
                    callback_data=f"select_office_{office.id}"
                )])
            
            keyboard_buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
            keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
            
            await callback.message.edit_text(
                "🏢 <b>Выберите офис</b>\n\n"
                "💡 Выберите ваш офис для заказа обеда",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
                parse_mode="HTML"
            )
            await state.set_state(OrderStates.choosing_office)
        
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("select_office_"))
async def callback_select_office(callback: CallbackQuery, state: FSMContext):
    office_id = int(callback.data.replace("select_office_", ""))
    await state.update_data(office_id=office_id)
    
    async for session in get_session():
        cafes = await get_all_cafes(session, office_id=office_id)
        
        if not cafes:
            await callback.message.edit_text(
                "\n"
                "   ⚠️ <b>Кафе недоступны</b>\n"
                "\n\n"
                "Для выбранного офиса пока нет доступных кафе.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="create_order")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        keyboard_buttons = []
        for cafe in cafes:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"☕ {cafe.name}",
                callback_data=f"select_cafe_{cafe.id}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="create_order")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
        "☕ <b>Выберите кафе</b>\n\n"
            "💡 Выберите кафе для заказа обеда",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
            parse_mode="HTML"
        )
        await state.set_state(OrderStates.choosing_cafe)
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("select_cafe_"))
async def callback_select_cafe(callback: CallbackQuery, state: FSMContext):
    cafe_id = int(callback.data.replace("select_cafe_", ""))
    await state.update_data(cafe_id=cafe_id)
    
    dates = []
    for i in range(7):
        date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=i)
        dates.append(date)
    
    keyboard_buttons = [
        [InlineKeyboardButton(
            text=f"{format_date(date)} {'(сегодня)' if i == 0 else ''}",
            callback_data=f"order_date_{date.strftime('%Y-%m-%d')}"
        )] for i, date in enumerate(dates)
    ]
    
    keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="create_order")])
    keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
    
    await callback.message.edit_text(
        "\n"
        "   📅 <b>Выберите дату заказа</b>\n"
        "\n\n"
        "💡 Вы можете заказать на ближайшие <b>7 дней</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
        parse_mode="HTML"
    )
    await state.set_state(OrderStates.choosing_date)
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("order_date_"))
async def callback_choose_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.replace("order_date_", "")
    order_date = datetime.strptime(date_str, "%Y-%m-%d")
    
    is_valid, error_msg = validate_order_date(order_date)
    if not is_valid:
        await callback.answer(error_msg, show_alert=True)
        return
    
    data = await state.get_data()
    cafe_id = data.get("cafe_id")
    
    if not cafe_id:
        await callback.answer("Ошибка: кафе не выбрано", show_alert=True)
        return
    
    async for session in get_session():
        deadline = await get_deadline_for_date(session, order_date, cafe_id=cafe_id)
        if deadline:
            now = datetime.now()
            if now >= deadline.deadline_time:
                await callback.answer(
                    f"Дедлайн заказа на эту дату уже прошел ({deadline.deadline_time.strftime('%H:%M')})",
                    show_alert=True
                )
                return
        
        await state.update_data(order_date=order_date)
        
        from sqlalchemy.orm import selectinload
        from models.cafe_menu import CafeMenu
        from models.dish import Dish
        from sqlalchemy import select
        
        menu_items_query = select(CafeMenu, Dish).join(Dish, CafeMenu.dish_id == Dish.id).where(
            CafeMenu.cafe_id == cafe_id,
            CafeMenu.date >= order_date.replace(hour=0, minute=0, second=0, microsecond=0),
            CafeMenu.date <= order_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        )
        result = await session.execute(menu_items_query)
        menu_items = result.all()
        
        if not menu_items:
            await callback.message.edit_text(
                f"⚠️ <b>Меню недоступно</b>\n\n"
                f"На <b>{format_date(order_date)}</b> меню пока не загружено.\n\n"
                "💡 Попробуйте выбрать другую дату.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад к выбору даты", callback_data=f"select_cafe_{cafe_id}")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        categories = {}
        for menu_item, dish in menu_items:
            if menu_item.available_quantity > 0:
                category = dish.category or "Без категории"
                if category not in categories:
                    categories[category] = []
                categories[category].append((dish, menu_item))
        
        if not categories:
            await callback.message.edit_text(
                f"😔 <b>Блюда закончились</b>\n\n"
                f"На <b>{format_date(order_date)}</b> все блюда уже разобраны.\n\n"
                "💡 Попробуйте выбрать другую дату.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад к выбору даты", callback_data=f"select_cafe_{cafe_id}")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        keyboard_buttons = []
        for category, items in categories.items():
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"📁 {category} ({len(items)})",
                callback_data=f"category_{category}_{date_str}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"select_cafe_{cafe_id}")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        cafe = await get_cafe_by_id(session, cafe_id)
        cafe_name = cafe.name if cafe else f"Кафе #{cafe_id}"
        
        await callback.message.edit_text(
            f"\n"
            f"   📋 <b>Меню {cafe_name}</b>\n"
            f"   📅 <b>{format_date(order_date)}</b>\n"
            f"\n\n"
            f"👇 <b>Выберите категорию:</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
            parse_mode="HTML"
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("category_"))
async def callback_show_category(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    category = "_".join(parts[1:-1])
    date_str = parts[-1]
    order_date = datetime.strptime(date_str, "%Y-%m-%d")
    
    data = await state.get_data()
    cafe_id = data.get("cafe_id")
    
    if not cafe_id:
        await callback.answer("Ошибка: кафе не выбрано", show_alert=True)
        return
    
    async for session in get_session():
        from sqlalchemy.orm import selectinload
        from models.cafe_menu import CafeMenu
        from models.dish import Dish
        from sqlalchemy import select
        
        menu_items_query = select(CafeMenu, Dish).join(Dish, CafeMenu.dish_id == Dish.id).where(
            CafeMenu.cafe_id == cafe_id,
            CafeMenu.date >= order_date.replace(hour=0, minute=0, second=0, microsecond=0),
            CafeMenu.date <= order_date.replace(hour=23, minute=59, second=59, microsecond=999999),
            (Dish.category == category) | ((Dish.category.is_(None)) & (category == "Без категории"))
        )
        result = await session.execute(menu_items_query)
        category_items = [(dish, menu_item) for menu_item, dish in result.all() 
                         if menu_item.available_quantity > 0]
        
        if not category_items:
            await callback.answer("В этой категории нет доступных блюд", show_alert=True)
            return
        
        keyboard_buttons = []
        for dish, menu_item in category_items:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"{dish.name} - {dish.price:.0f} ₽ (осталось: {menu_item.available_quantity})",
                callback_data=f"dish_{dish.id}_{date_str}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад к категориям", callback_data=f"order_date_{date_str}")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
            f"\n"
            f"   📁 <b>{category}</b>\n"
            f"\n\n"
            f"👇 <b>Выберите блюдо:</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
            parse_mode="HTML"
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("dish_"))
async def callback_choose_dish(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора блюда из меню
    Показывает детали блюда и позволяет выбрать количество
    """
    parts = callback.data.split("_")
    dish_id = int(parts[1])
    date_str = parts[2]
    
    async for session in get_session():
        dish = await get_dish_by_id(session, dish_id)
        if not dish:
            await callback.answer("Блюдо не найдено", show_alert=True)
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➖", callback_data="qty_-1"), 
             InlineKeyboardButton(text="1", callback_data="qty_1"),
             InlineKeyboardButton(text="➕", callback_data="qty_+1")],
            [InlineKeyboardButton(text="⌨️ Ввести вручную", callback_data="qty_manual")],
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_dish")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"order_date_{date_str}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        # Проверяем, есть ли уже это блюдо в корзине
        order_date = datetime.strptime(date_str, "%Y-%m-%d")
        data = await state.get_data()
        
        # Сохраняем order_date если его еще нет
        if not data.get("order_date"):
            await state.update_data(order_date=order_date)
        
        cart = data.get("cart", [])
        already_in_cart = 0
        for item in cart:
            if item["dish_id"] == dish_id:
                already_in_cart = item["quantity"]
                break
        
        menu_item_check = await get_menu_item(session, order_date, dish_id)
        available_info = f"Доступно: {menu_item_check.available_quantity} порций"
        if already_in_cart > 0:
            available_info += f" (в корзине: {already_in_cart})"
        
        await state.update_data(dish_id=dish_id, dish_price=dish.price, quantity=1, order_date=order_date)
        await state.set_state(OrderStates.choosing_quantity)
        
        await callback.message.edit_text(
            f"🍽️ <b>{dish.name}</b>\n\n"
            f"\n"
            f"📝 <b>Описание:</b>\n"
            f"{dish.description or '<i>Без описания</i>'}\n\n"
            f"💰 <b>Цена за порцию:</b> {dish.price:.0f} ₽\n"
            f"📦 {available_info}\n\n"
            f"📊 <b>Количество:</b> 1\n"
            f"💵 <b>Итого:</b> {dish.price:.0f} ₽",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("qty_"))
async def callback_change_quantity(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_qty = data.get("quantity", 1)
    dish_id = data.get("dish_id")
    order_date = data.get("order_date")
    
    if not dish_id or not order_date:
        await callback.answer("Ошибка: данные не найдены", show_alert=True)
        return
    
    async for session in get_session():
        dish = await get_dish_by_id(session, dish_id)
        menu_item = await get_menu_item(session, order_date, dish_id)
        
        if not dish or not menu_item:
            await callback.answer("Блюдо не найдено", show_alert=True)
            return
        
        # Учитываем количество, уже добавленное в корзину
        cart = data.get("cart", [])
        already_in_cart = 0
        for item in cart:
            if item["dish_id"] == dish_id:
                already_in_cart = item["quantity"]
                break
        
        # Максимальное доступное количество = доступно + уже в корзине
        # (потому что при подтверждении старое количество заменяется новым)
        max_available = menu_item.available_quantity + already_in_cart
        
        if callback.data == "qty_+1":
            new_qty = min(current_qty + 1, max_available)
        elif callback.data == "qty_-1":
            new_qty = max(current_qty - 1, 1)
        elif callback.data == "qty_manual":
            # Это должно обрабатываться отдельным обработчиком, но на всякий случай
            await callback.answer()
            return
        else:
            # Пытаемся извлечь число из callback_data (например, "qty_5")
            try:
                parts = callback.data.split("_")
                if len(parts) >= 2:
                    qty_val = int(parts[1])
                    new_qty = min(max(qty_val, 1), max_available)
                else:
                    await callback.answer("Неверный формат", show_alert=True)
                    return
            except (ValueError, IndexError):
                await callback.answer("Ошибка обработки", show_alert=True)
                return
        
        await state.update_data(quantity=new_qty)
        
        total = dish.price * new_qty
        date_str = order_date.strftime("%Y-%m-%d")
        
        # Отключаем кнопки, если достигнут лимит
        btn_plus_disabled = new_qty >= max_available
        btn_minus_disabled = new_qty <= 1
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➖", callback_data="qty_-1"), 
             InlineKeyboardButton(text=str(new_qty), callback_data="qty_1"),
             InlineKeyboardButton(text="➕", callback_data="qty_+1")],
            [InlineKeyboardButton(text="⌨️ Ввести вручную", callback_data="qty_manual")],
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_dish")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"order_date_{date_str}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        available_info = f"Доступно: {menu_item.available_quantity} порций"
        if already_in_cart > 0:
            available_info += f" (в корзине: {already_in_cart})"
        
        await callback.message.edit_text(
            f"🍽️ <b>{dish.name}</b>\n\n"
            f"📝 <b>Описание:</b>\n"
            f"{dish.description or '<i>Без описания</i>'}\n\n"
            f"💰 <b>Цена за порцию:</b> {dish.price:.0f} ₽\n"
            f"📦 {available_info}\n\n"
            f"📊 <b>Количество:</b> {new_qty}\n"
            f"💵 <b>Итого:</b> {total:.0f} ₽",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await callback.answer()

@router.callback_query(lambda c: c.data == "qty_manual")
async def callback_qty_manual(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    dish_id = data.get("dish_id")
    order_date = data.get("order_date")
    
    if not dish_id or not order_date:
        await callback.answer("Ошибка: данные не найдены", show_alert=True)
        return
    
    async for session in get_session():
        dish = await get_dish_by_id(session, dish_id)
        menu_item = await get_menu_item(session, order_date, dish_id)
        
        if not dish or not menu_item:
            await callback.answer("Блюдо не найдено", show_alert=True)
            return
        
        # Учитываем количество в корзине
        cart = data.get("cart", [])
        already_in_cart = 0
        for item in cart:
            if item["dish_id"] == dish_id:
                already_in_cart = item["quantity"]
                break
        
        max_available = menu_item.available_quantity + already_in_cart
        available_info = f"Доступно: {menu_item.available_quantity} порций"
        if already_in_cart > 0:
            available_info += f" (в корзине: {already_in_cart})"
        
        await state.set_state(OrderStates.choosing_quantity)
        await callback.message.edit_text(
            f"⌨️ <b>Введите количество вручную</b>\n\n"
            f"📦 {available_info}\n"
            f"💡 Максимум: {max_available} порций\n\n"
            f"Введите число от 1 до {max_available}:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"dish_{dish_id}_{order_date.strftime('%Y-%m-%d')}")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()

@router.message(OrderStates.choosing_quantity)
async def process_manual_quantity(message: Message, state: FSMContext):
    try:
        quantity = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число:")
        return
    
    data = await state.get_data()
    dish_id = data.get("dish_id")
    order_date = data.get("order_date")
    
    if not dish_id or not order_date:
        async for session in get_session():
            from utils.keyboards import get_main_menu_keyboard
            from services.user_service import is_admin, get_or_create_user
            user = await get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.full_name)
            user_is_admin = await is_admin(session, user.telegram_id)
            await message.answer(
                "❌ Ошибка: данные не найдены. Начните заказ заново.",
                reply_markup=get_main_menu_keyboard(is_admin=user_is_admin)
            )
        await state.clear()
        return
    
    async for session in get_session():
        from services.menu_service import get_dish_by_id, get_menu_item
        dish = await get_dish_by_id(session, dish_id)
        menu_item = await get_menu_item(session, order_date, dish_id)
        
        if not dish or not menu_item:
            await message.answer("❌ Блюдо не найдено. Начните заказ заново.")
            await state.clear()
            return
        
        # Учитываем количество в корзине
        cart = data.get("cart", [])
        already_in_cart = 0
        for item in cart:
            if item["dish_id"] == dish_id:
                already_in_cart = item["quantity"]
                break
        
        max_available = menu_item.available_quantity + already_in_cart
        
        if quantity < 1:
            await message.answer(f"❌ Количество должно быть больше 0. Введите число от 1 до {max_available}:")
            return
        
        if quantity > max_available:
            await message.answer(
                f"❌ Доступно только {menu_item.available_quantity} порций "
                f"{'(уже в корзине: ' + str(already_in_cart) + ')' if already_in_cart > 0 else ''}.\n"
                f"Введите число от 1 до {max_available}:"
            )
            return
        
        await state.update_data(quantity=quantity)
        
        total = dish.price * quantity
        date_str = order_date.strftime("%Y-%m-%d")
        
        available_info = f"Доступно: {menu_item.available_quantity} порций"
        if already_in_cart > 0:
            available_info += f" (в корзине: {already_in_cart})"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➖", callback_data="qty_-1"), 
             InlineKeyboardButton(text=str(quantity), callback_data="qty_1"),
             InlineKeyboardButton(text="➕", callback_data="qty_+1")],
            [InlineKeyboardButton(text="⌨️ Ввести вручную", callback_data="qty_manual")],
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_dish")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"order_date_{date_str}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        await message.answer(
            f"🍽️ <b>{dish.name}</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 <b>Описание:</b>\n"
            f"{dish.description or 'Без описания'}\n\n"
            f"💰 <b>Цена за порцию:</b> {dish.price:.0f} ₽\n"
            f"📦 {available_info}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>Количество:</b> {quantity}\n"
            f"💵 <b>Итого:</b> {total:.0f} ₽",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@router.callback_query(lambda c: c.data == "confirm_dish")
async def callback_confirm_dish(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    dish_id = data.get("dish_id")
    quantity = data.get("quantity", 1)
    order_date = data.get("order_date")
    
    if not dish_id or not order_date:
        await callback.answer("Ошибка: данные не найдены", show_alert=True)
        return
    
    async for session in get_session():
        dish = await get_dish_by_id(session, dish_id)
        menu_item = await get_menu_item(session, order_date, dish_id)
        
        if not dish or not menu_item:
            await callback.answer("Блюдо не найдено", show_alert=True)
            return
        
        if menu_item.available_quantity < quantity:
            await callback.answer(
                f"Доступно только {menu_item.available_quantity} порций",
                show_alert=True
            )
            return
        
        cart = data.get("cart", [])
        
        # Находим существующее блюдо в корзине
        existing_item = None
        for item in cart:
            if item["dish_id"] == dish_id:
                existing_item = item
                break
        
        # Проверяем итоговое количество (если блюдо уже есть, заменяем количество)
        total_requested = quantity
        if existing_item:
            # Если блюдо уже в корзине, заменяем количество
            # Но нужно проверить доступность с учетом старого количества
            old_quantity = existing_item["quantity"]
            # Доступно = menu_item.available_quantity + old_quantity (которое мы освобождаем)
            max_with_replacement = menu_item.available_quantity + old_quantity
            if quantity > max_with_replacement:
                await callback.answer(
                    f"Доступно только {menu_item.available_quantity} порций "
                    f"(в корзине было: {old_quantity})",
                    show_alert=True
                )
                return
            existing_item["quantity"] = quantity
        else:
            # Новое блюдо - просто проверяем доступность
            if quantity > menu_item.available_quantity:
                await callback.answer(
                    f"Доступно только {menu_item.available_quantity} порций",
                    show_alert=True
                )
                return
            cart.append({
                "dish_id": dish_id,
                "dish_name": dish.name,
                "quantity": quantity,
                "price": dish.price
            })
        
        await state.update_data(cart=cart)
        
        total = sum(item["price"] * item["quantity"] for item in cart)
        
        cart_text = "\n".join([
            f"{i+1}. <b>{item['dish_name']}</b>\n"
            f"   x{item['quantity']} × {item['price']:.0f} ₽ = {item['price'] * item['quantity']:.0f} ₽"
            for i, item in enumerate(cart)
        ])
        
        keyboard_buttons = []
        # Кнопки редактирования для каждого блюда
        for i, item in enumerate(cart):
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"✏️ {item['dish_name']} (x{item['quantity']})",
                    callback_data=f"edit_cart_item_{item['dish_id']}"
                )
            ])
            keyboard_buttons.append([
                InlineKeyboardButton(text="➖ Уменьшить", callback_data=f"cart_item_dec_{item['dish_id']}"),
                InlineKeyboardButton(text="➕ Увеличить", callback_data=f"cart_item_inc_{item['dish_id']}"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"cart_item_remove_{item['dish_id']}")
            ])
        
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="➕ Добавить еще", callback_data=f"order_date_{order_date.strftime('%Y-%m-%d')}")],
            [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="finalize_order")],
            [InlineKeyboardButton(text="🗑️ Очистить корзину", callback_data="clear_cart")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        cart_display = f"""
   🛒 <b>Ваша корзина</b>

{cart_text}

💰 <b>Итого:</b> {total:.0f} ₽
📅 <b>Дата заказа:</b> {format_date(order_date)}

💡 <i>Нажмите на блюдо для редактирования</i>
        """
        
        await callback.message.edit_text(
            cart_display,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer("Блюдо добавлено в корзину")

@router.callback_query(lambda c: c.data == "return_to_cart")
async def callback_return_to_cart(callback: CallbackQuery, state: FSMContext):
    """Возврат к незавершенной корзине"""
    data = await state.get_data()
    cart = data.get("cart", [])
    order_date = data.get("order_date")
    
    if not cart or not order_date:
        await callback.answer("Корзина пуста", show_alert=True)
        await callback_create_order(callback, state)
        return
    
    total = sum(item["price"] * item["quantity"] for item in cart)
    cart_text = "\n".join([
        f"{i+1}. <b>{item['dish_name']}</b>\n"
        f"   x{item['quantity']} × {item['price']:.0f} ₽ = {item['price'] * item['quantity']:.0f} ₽"
        for i, item in enumerate(cart)
    ])
    
    keyboard_buttons = []
    # Кнопки редактирования для каждого блюда
    for i, item in enumerate(cart):
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"✏️ {item['dish_name']} (x{item['quantity']})",
                callback_data=f"edit_cart_item_{item['dish_id']}"
            )
        ])
        keyboard_buttons.append([
            InlineKeyboardButton(text="➖ Уменьшить", callback_data=f"cart_item_dec_{item['dish_id']}"),
            InlineKeyboardButton(text="➕ Увеличить", callback_data=f"cart_item_inc_{item['dish_id']}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"cart_item_remove_{item['dish_id']}")
        ])
    
    keyboard_buttons.extend([
        [InlineKeyboardButton(text="➕ Добавить еще", callback_data=f"order_date_{order_date.strftime('%Y-%m-%d')}")],
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="finalize_order")],
        [InlineKeyboardButton(text="🗑️ Очистить корзину", callback_data="clear_cart")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    cart_display = f"""
🛒 <b>Ваша корзина</b>

{cart_text}

💰 <b>Итого:</b> {total:.0f} ₽
📅 <b>Дата заказа:</b> {format_date(order_date)}

💡 <i>Нажмите на блюдо для редактирования</i>
    """
    
    await callback.message.edit_text(
        cart_display,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("edit_cart_item_"))
async def callback_edit_cart_item(callback: CallbackQuery, state: FSMContext):
    """Редактирование конкретного блюда в корзине"""
    dish_id = int(callback.data.replace("edit_cart_item_", ""))
    data = await state.get_data()
    cart = data.get("cart", [])
    order_date = data.get("order_date")
    
    if not order_date:
        await callback.answer("Ошибка: дата не найдена", show_alert=True)
        return
    
    # Находим блюдо в корзине
    cart_item = None
    for item in cart:
        if item["dish_id"] == dish_id:
            cart_item = item
            break
    
    if not cart_item:
        await callback.answer("Блюдо не найдено в корзине", show_alert=True)
        return
    
    async for session in get_session():
        dish = await get_dish_by_id(session, dish_id)
        menu_item = await get_menu_item(session, order_date, dish_id)
        
        if not dish or not menu_item:
            await callback.answer("Блюдо не найдено", show_alert=True)
            return
        
        # Максимальное количество с учетом уже в корзине
        max_available = menu_item.available_quantity + cart_item["quantity"]
        
        await state.update_data(
            dish_id=dish_id,
            dish_price=dish.price,
            quantity=cart_item["quantity"],
            editing_cart_item=True
        )
        
        total = dish.price * cart_item["quantity"]
        date_str = order_date.strftime("%Y-%m-%d")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➖", callback_data="cart_edit_qty_-1"), 
             InlineKeyboardButton(text=str(cart_item["quantity"]), callback_data="cart_edit_qty_1"),
             InlineKeyboardButton(text="➕", callback_data="cart_edit_qty_+1")],
            [InlineKeyboardButton(text="⌨️ Ввести вручную", callback_data="cart_edit_qty_manual")],
            [InlineKeyboardButton(text="✅ Сохранить", callback_data="cart_item_save")],
            [InlineKeyboardButton(text="🗑️ Удалить из корзины", callback_data=f"cart_item_remove_{dish_id}")],
            [InlineKeyboardButton(text="◀️ Назад к корзине", callback_data="return_to_cart")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        await callback.message.edit_text(
            f"\n"
            f"   ✏️ <b>Редактирование</b>\n"
            f"\n\n"
            f"🍽️ <b>{dish.name}</b>\n\n"
            f"📝 <b>Описание:</b>\n"
            f"{dish.description or '<i>Без описания</i>'}\n\n"
            f"💰 <b>Цена за порцию:</b> {dish.price:.0f} ₽\n"
            f"📦 Доступно: {menu_item.available_quantity} порций\n"
            f"   (в корзине: {cart_item['quantity']})\n\n"
            f"📊 <b>Текущее количество:</b> {cart_item['quantity']}\n"
            f"💵 <b>Итого:</b> {total:.0f} ₽",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("cart_edit_qty_"))
async def callback_cart_edit_qty(callback: CallbackQuery, state: FSMContext):
    """Изменение количества при редактировании блюда в корзине"""
    data = await state.get_data()
    dish_id = data.get("dish_id")
    order_date = data.get("order_date")
    current_qty = data.get("quantity", 1)
    
    if not dish_id or not order_date:
        await callback.answer("Ошибка: данные не найдены", show_alert=True)
        return
    
    async for session in get_session():
        dish = await get_dish_by_id(session, dish_id)
        menu_item = await get_menu_item(session, order_date, dish_id)
        
        if not dish or not menu_item:
            await callback.answer("Блюдо не найдено", show_alert=True)
            return
        
        # Находим текущее количество в корзине (кроме редактируемого)
        cart = data.get("cart", [])
        already_in_cart = 0
        for item in cart:
            if item["dish_id"] == dish_id:
                already_in_cart = item["quantity"]
                break
        
        # Максимальное количество
        max_available = menu_item.available_quantity + already_in_cart
        
        if callback.data == "cart_edit_qty_+1":
            new_qty = min(current_qty + 1, max_available)
        elif callback.data == "cart_edit_qty_-1":
            new_qty = max(current_qty - 1, 1)
        elif callback.data == "cart_edit_qty_manual":
            await state.set_state(OrderStates.editing_cart_item)
            await callback.message.edit_text(
                f"⌨️ <b>Введите новое количество</b>\n\n"
                f"📦 Доступно: {menu_item.available_quantity} порций\n"
                f"💡 Текущее в корзине: {already_in_cart}\n"
                f"💡 Максимум: {max_available} порций\n\n"
                f"Введите число от 1 до {max_available}:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_cart_item_{dish_id}")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return
        else:
            # Пытаемся извлечь число из callback_data (например, "cart_edit_qty_5")
            try:
                parts = callback.data.split("_")
                if len(parts) >= 4:
                    qty_val = int(parts[-1])
                    new_qty = min(max(qty_val, 1), max_available)
                else:
                    await callback.answer("Ошибка обработки", show_alert=True)
                    return
            except (ValueError, IndexError):
                await callback.answer("Ошибка обработки", show_alert=True)
                return
        
        await state.update_data(quantity=new_qty)
        
        total = dish.price * new_qty
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➖", callback_data="cart_edit_qty_-1"), 
             InlineKeyboardButton(text=str(new_qty), callback_data="cart_edit_qty_1"),
             InlineKeyboardButton(text="➕", callback_data="cart_edit_qty_+1")],
            [InlineKeyboardButton(text="⌨️ Ввести вручную", callback_data="cart_edit_qty_manual")],
            [InlineKeyboardButton(text="✅ Сохранить", callback_data="cart_item_save")],
            [InlineKeyboardButton(text="🗑️ Удалить из корзины", callback_data=f"cart_item_remove_{dish_id}")],
            [InlineKeyboardButton(text="◀️ Назад к корзине", callback_data="return_to_cart")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        await callback.message.edit_text(
            f"\n"
            f"   ✏️ <b>Редактирование</b>\n"
            f"\n\n"
            f"🍽️ <b>{dish.name}</b>\n\n"
            f"📝 <b>Описание:</b>\n"
            f"{dish.description or '<i>Без описания</i>'}\n\n"
            f"💰 <b>Цена за порцию:</b> {dish.price:.0f} ₽\n"
            f"📦 Доступно: {menu_item.available_quantity} порций\n"
            f"   (было в корзине: {already_in_cart})\n\n"
            f"📊 <b>Новое количество:</b> {new_qty}\n"
            f"💵 <b>Итого:</b> {total:.0f} ₽",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await callback.answer()

@router.message(OrderStates.editing_cart_item)
async def process_cart_item_manual_qty(message: Message, state: FSMContext):
    """Обработка ручного ввода количества при редактировании корзины"""
    try:
        quantity = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число:")
        return
    
    data = await state.get_data()
    dish_id = data.get("dish_id")
    order_date = data.get("order_date")
    
    if not dish_id or not order_date:
        await message.answer("❌ Ошибка: данные не найдены")
        await state.clear()
        return
    
    async for session in get_session():
        from services.menu_service import get_dish_by_id, get_menu_item
        dish = await get_dish_by_id(session, dish_id)
        menu_item = await get_menu_item(session, order_date, dish_id)
        
        if not dish or not menu_item:
            await message.answer("❌ Блюдо не найдено")
            await state.clear()
            return
        
        # Текущее количество в корзине
        cart = data.get("cart", [])
        already_in_cart = 0
        for item in cart:
            if item["dish_id"] == dish_id:
                already_in_cart = item["quantity"]
                break
        
        max_available = menu_item.available_quantity + already_in_cart
        
        if quantity < 1:
            await message.answer(f"❌ Количество должно быть больше 0. Введите число от 1 до {max_available}:")
            return
        
        if quantity > max_available:
            await message.answer(
                f"❌ Доступно только {menu_item.available_quantity} порций "
                f"(в корзине было: {already_in_cart}).\n"
                f"Введите число от 1 до {max_available}:"
            )
            return
        
        await state.update_data(quantity=quantity)
        
        total = dish.price * quantity
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➖", callback_data="cart_edit_qty_-1"), 
             InlineKeyboardButton(text=str(quantity), callback_data="cart_edit_qty_1"),
             InlineKeyboardButton(text="➕", callback_data="cart_edit_qty_+1")],
            [InlineKeyboardButton(text="⌨️ Ввести вручную", callback_data="cart_edit_qty_manual")],
            [InlineKeyboardButton(text="✅ Сохранить", callback_data="cart_item_save")],
            [InlineKeyboardButton(text="🗑️ Удалить из корзины", callback_data=f"cart_item_remove_{dish_id}")],
            [InlineKeyboardButton(text="◀️ Назад к корзине", callback_data="return_to_cart")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        await message.answer(
            f"\n"
            f"   ✏️ <b>Редактирование</b>\n"
            f"\n\n"
            f"🍽️ <b>{dish.name}</b>\n\n"
            f"📝 <b>Описание:</b>\n"
            f"{dish.description or '<i>Без описания</i>'}\n\n"
            f"💰 <b>Цена за порцию:</b> {dish.price:.0f} ₽\n"
            f"📦 Доступно: {menu_item.available_quantity} порций\n\n"
            f"\n"
            f"📊 <b>Новое количество:</b> {quantity}\n"
            f"💵 <b>Итого:</b> {total:.0f} ₽\n"
            f"",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@router.callback_query(lambda c: c.data == "cart_item_save")
async def callback_cart_item_save(callback: CallbackQuery, state: FSMContext):
    """Сохранение изменений блюда в корзине"""
    data = await state.get_data()
    dish_id = data.get("dish_id")
    new_quantity = data.get("quantity", 1)
    order_date = data.get("order_date")
    
    if not dish_id or not order_date:
        await callback.answer("Ошибка: данные не найдены", show_alert=True)
        return
    
    async for session in get_session():
        dish = await get_dish_by_id(session, dish_id)
        menu_item = await get_menu_item(session, order_date, dish_id)
        
        if not dish or not menu_item:
            await callback.answer("Блюдо не найдено", show_alert=True)
            return
        
        # Проверка доступности
        # Находим старое количество в корзине
        old_quantity = 0
        for item in cart:
            if item["dish_id"] == dish_id:
                old_quantity = item["quantity"]
                break
        
        # Проверяем, не превышаем ли доступное количество
        # Доступно = menu_item.available_quantity + старое_количество_в_корзине
        # Новое количество должно быть <= доступно
        max_available = menu_item.available_quantity + old_quantity
        
        if new_quantity > max_available:
            await callback.answer(
                f"Доступно только {menu_item.available_quantity} порций",
                show_alert=True
            )
            return
        
        # Обновляем корзину
        for item in cart:
            if item["dish_id"] == dish_id:
                item["quantity"] = new_quantity
                break
        
        await state.update_data(cart=cart, editing_cart_item=False)
        
        # Возвращаемся к корзине
        await callback_return_to_cart(callback, state)
        await callback.answer("Количество обновлено")

@router.callback_query(lambda c: c.data.startswith("cart_item_dec_") or c.data.startswith("cart_item_inc_"))
async def callback_cart_item_change_qty(callback: CallbackQuery, state: FSMContext):
    """Быстрое изменение количества в корзине (+/-1)"""
    try:
        parts = callback.data.split("_")
        if len(parts) < 5:
            await callback.answer("Ошибка: неверный формат команды", show_alert=True)
            return
        action = parts[3]  # "dec" or "inc"
        dish_id = int(parts[4])
    except (ValueError, IndexError) as e:
        await callback.answer("Ошибка обработки команды", show_alert=True)
        return
    data = await state.get_data()
    cart = data.get("cart", [])
    order_date = data.get("order_date")
    
    if not order_date:
        await callback.answer("Ошибка: дата не найдена", show_alert=True)
        return
    
    # Находим блюдо в корзине
    cart_item = None
    for item in cart:
        if item["dish_id"] == dish_id:
            cart_item = item
            break
    
    if not cart_item:
        await callback.answer("Блюдо не найдено в корзине", show_alert=True)
        return
    
    async for session in get_session():
        menu_item = await get_menu_item(session, order_date, dish_id)
        
        if not menu_item:
            await callback.answer("Блюдо не найдено", show_alert=True)
            return
        
        if action == "dec":
            if cart_item["quantity"] > 1:
                cart_item["quantity"] -= 1
            else:
                await callback.answer("Минимальное количество: 1", show_alert=True)
                return
        else:  # inc
            # Максимальное = доступно + текущее в корзине (т.к. при подтверждении заменяется)
            max_available = menu_item.available_quantity + cart_item["quantity"]
            current_in_cart = cart_item["quantity"]
            
            if current_in_cart < max_available:
                cart_item["quantity"] += 1
            else:
                await callback.answer(
                    f"Доступно только {menu_item.available_quantity} порций",
                    show_alert=True
                )
                return
        
        await state.update_data(cart=cart)
        await callback_return_to_cart(callback, state)
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("cart_item_remove_"))
async def callback_cart_item_remove(callback: CallbackQuery, state: FSMContext):
    """Удаление блюда из корзины"""
    try:
        dish_id = int(callback.data.replace("cart_item_remove_", ""))
    except ValueError:
        await callback.answer("Ошибка: неверный формат команды", show_alert=True)
        return
    
    data = await state.get_data()
    cart = data.get("cart", [])
    
    # Удаляем блюдо из корзины
    cart = [item for item in cart if item["dish_id"] != dish_id]
    
    if not cart:
        # Корзина пуста
        await state.update_data(cart=[], order_date=None)
        await callback.message.edit_text(
            "\n"
            "🛒 <b>Корзина пуста</b>\n\n"
            "💡 Добавьте блюда в корзину для оформления заказа.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Создать заказ", callback_data="create_order")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer("Блюдо удалено из корзины")
        return
    
    await state.update_data(cart=cart)
    await callback_return_to_cart(callback, state)
    await callback.answer("Блюдо удалено из корзины")

@router.callback_query(lambda c: c.data == "clear_cart")
async def callback_clear_cart(callback: CallbackQuery, state: FSMContext):
    await state.update_data(cart=[], order_date=None)
    await callback.message.edit_text(
            "🗑️ <b>Корзина очищена</b>\n\n"
        "💡 Вы можете начать новый заказ.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Создать заказ", callback_data="create_order")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()
    # НЕ очищаем state полностью, только корзину, чтобы пользователь мог продолжить

@router.callback_query(lambda c: c.data == "finalize_order")
async def callback_finalize_order(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик финализации заказа
    Создает заказ в БД, обновляет доступность блюд и отправляет уведомления
    """
    data = await state.get_data()
    cart = data.get("cart", [])
    order_date = data.get("order_date")
    
    if not cart:
        await callback.answer(
            "❌ Корзина пуста!\n\n"
            "Добавьте блюда в корзину перед оформлением заказа.",
            show_alert=True
        )
        return
    
    if not order_date:
        await callback.answer(
            "❌ Ошибка: дата заказа не найдена!\n\n"
            "Пожалуйста, начните заказ заново.",
            show_alert=True
        )
        await state.clear()
        return
    
    await callback.message.bot.send_chat_action(callback.message.chat.id, "typing")
    msg = await callback.message.answer("⏳ Проверка доступности блюд...")
    
    async for session in get_session():
        # Финальная проверка доступности всех блюд в корзине
        unavailable_items = []
        for item in cart:
            menu_item = await get_menu_item(session, order_date, item["dish_id"])
            if not menu_item or menu_item.available_quantity < item["quantity"]:
                dish = await get_dish_by_id(session, item["dish_id"])
                dish_name = dish.name if dish else f"ID {item['dish_id']}"
                available = menu_item.available_quantity if menu_item else 0
                unavailable_items.append(f"{dish_name}: доступно {available}, запрошено {item['quantity']}")
        
        if unavailable_items:
            await msg.delete()
            unavailable_text = "\n".join([f"  • {item}" for item in unavailable_items])
            await callback.message.edit_text(
                f"\n"
                f"   ⚠️ <b>Внимание!</b>\n"
                f"\n\n"
                f"Некоторые блюда недоступны в нужном количестве:\n\n"
                f"{unavailable_text}\n\n"
                f"💡 Пожалуйста, отредактируйте корзину.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🛒 Вернуться к корзине", callback_data="return_to_cart")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        await msg.edit_text("⏳ Обработка заказа...")
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.full_name
        )
        
        from services.order_service import create_order, get_user_orders
        from models.order import OrderStatus
        
        existing_orders = await get_user_orders(
            session, 
            user.id, 
            status=OrderStatus.PENDING,
            date_from=order_date.replace(hour=0, minute=0, second=0, microsecond=0),
            date_to=order_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        )
        
        if existing_orders:
            existing_order = existing_orders[0]
            # Загружаем связанные объекты перед форматированием
            from sqlalchemy.orm import selectinload
            from sqlalchemy import select
            from models.order import Order, OrderItem
            result = await session.execute(
                select(Order)
                .where(Order.id == existing_order.id)
                .options(selectinload(Order.items).selectinload(OrderItem.dish))
            )
            existing_order = result.scalar_one()
            
            from utils.formatters import format_order
            order_text = format_order(existing_order)
            
            await msg.delete()
            await callback.message.edit_text(
                f"\n"
                f"   ⚠️ <b>Внимание!</b>\n"
                f"\n\n"
                f"У вас уже есть заказ на эту дату!\n\n"
                f"{order_text}\n\n"
                f"💡 Вы можете отредактировать существующий заказ или отменить его перед созданием нового.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✏️ Редактировать заказ", callback_data=f"edit_order_{existing_order.id}")],
                    [InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"cancel_order_{existing_order.id}")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="start")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            await state.clear()
            return
        
        order_items = []
        for item in cart:
            order_items.append({
                "dish_id": item["dish_id"],
                "quantity": item["quantity"],
                "price": item["price"]
            })
        
        try:
            order = await create_order(session, user.id, order_date, order_items)
        except ValueError as e:
            await msg.delete()
            await callback.answer(
                str(e),
                show_alert=True
            )
            await state.clear()
            return
        
        # Загружаем связанные объекты перед форматированием
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        from models.order import Order, OrderItem
        result = await session.execute(
            select(Order)
            .where(Order.id == order.id)
            .options(selectinload(Order.items).selectinload(OrderItem.dish))
        )
        order = result.scalar_one()
        
        from utils.formatters import format_order
        from services.notification_service import notify_admins_about_new_order
        
        order_text = format_order(order)
        admin_notification = (
            f"Заказ #{order.id}\n"
            f"Пользователь: {user.full_name or user.username or user.telegram_id}\n"
            f"Дата: {format_date(order.order_date)}\n"
            f"Сумма: {order.total_amount:.0f} ₽\n\n"
            f"{order_text}"
        )
        
        await notify_admins_about_new_order(callback.message.bot, admin_notification)
        
        await msg.delete()
        success_message = f"""
✅ <b>Заказ успешно создан!</b>

{order_text}

💡 <i>Вы можете отслеживать статус заказа в разделе '📦 Мои заказы'.</i>
        """
        
        await callback.message.edit_text(
            success_message,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()
        # Очищаем корзину после успешного оформления
        await state.update_data(cart=[], order_date=None)
        await state.clear()

