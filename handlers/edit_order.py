from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.database import get_session
from services.user_service import get_or_create_user
from services.order_service import get_order_by_id, update_order, remove_item_from_order, add_item_to_order
from services.menu_service import get_dish_by_id, get_menu_item
from models.order import OrderStatus
from utils.formatters import format_order, format_date
from datetime import datetime

router = Router()

class EditOrderStates(StatesGroup):
    choosing_action = State()
    removing_item = State()
    adding_dish = State()

@router.callback_query(lambda c: c.data.startswith("edit_order_"))
async def callback_edit_order(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.replace("edit_order_", ""))
    
    async for session in get_session():
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.full_name
        )
        
        order = await get_order_by_id(session, order_id, user.id)
        
        if not order:
            from utils.keyboards import get_back_keyboard
            await callback.message.edit_text(
                "❌ Заказ не найден",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return
        
        if order.status != OrderStatus.PENDING:
            from utils.keyboards import get_back_keyboard
            await callback.message.edit_text(
                "⚠️ Можно редактировать только активные заказы",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return
        
        from services.deadline_service import get_deadline_for_date
        deadline = await get_deadline_for_date(session, order.order_date, 
                                               office_id=user.office_id, 
                                               cafe_id=order.cafe_id)
        
        if deadline:
            now = datetime.now()
            if now >= deadline.deadline_time:
                from utils.keyboards import get_back_keyboard
                await callback.message.edit_text(
                    f"⚠️ <b>Редактирование недоступно</b>\n\n"
                    f"Дедлайн заказа на {format_date(order.order_date)} уже прошел.\n"
                    f"Дедлайн был: {deadline.deadline_time.strftime('%H:%M')}",
                    reply_markup=get_back_keyboard(),
                    parse_mode="HTML"
                )
                await callback.answer()
                return
        
        items_text = "\n".join([
            f"{i+1}. {item.dish.name} x{item.quantity} - {item.price * item.quantity:.0f} ₽"
            for i, item in enumerate(order.items)
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить блюдо", callback_data=f"add_to_order_{order.id}")],
            *[[InlineKeyboardButton(
                text=f"❌ Удалить: {item.dish.name}",
                callback_data=f"remove_item_{order.id}_{item.id}"
            )] for item in order.items],
            [InlineKeyboardButton(text="✅ Сохранить", callback_data=f"save_order_{order.id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"order_details_{order.id}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        await state.update_data(order_id=order_id)
        await state.set_state(EditOrderStates.choosing_action)
        
        await callback.message.edit_text(
            f"✏️ Редактирование заказа #{order.id}\n\n"
            f"Дата: {format_date(order.order_date)}\n\n"
            f"Текущие позиции:\n{items_text}\n\n"
            f"Итого: {order.total_amount:.0f} ₽",
            reply_markup=keyboard
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("remove_item_"))
async def callback_remove_item(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    order_id = int(parts[2])
    item_id = int(parts[3])
    
    async for session in get_session():
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.full_name
        )
        
        from services.order_service import remove_item_from_order
        success = await remove_item_from_order(session, order_id, user.id, item_id)
        
        if success:
            order = await get_order_by_id(session, order_id, user.id)
            items_text = "\n".join([
                f"{i+1}. {item.dish.name} x{item.quantity} - {item.price * item.quantity:.0f} ₽"
                for i, item in enumerate(order.items)
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить блюдо", callback_data=f"add_to_order_{order.id}")],
                *[[InlineKeyboardButton(
                    text=f"❌ Удалить: {item.dish.name}",
                    callback_data=f"remove_item_{order.id}_{item.id}"
                )] for item in order.items],
                [InlineKeyboardButton(text="✅ Сохранить", callback_data=f"save_order_{order.id}")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"order_details_{order.id}")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ])
            
            await callback.message.edit_text(
                f"✏️ Редактирование заказа #{order.id}\n\n"
                f"Дата: {format_date(order.order_date)}\n\n"
                f"Текущие позиции:\n{items_text}\n\n"
                f"Итого: {order.total_amount:.0f} ₽",
                reply_markup=keyboard
            )
            await callback.answer("Позиция удалена")
        else:
            from utils.keyboards import get_back_keyboard
            await callback.message.edit_text(
                "❌ Не удалось удалить позицию",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()

@router.callback_query(lambda c: c.data.startswith("add_to_order_"))
async def callback_add_to_order(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.replace("add_to_order_", ""))
    
    async for session in get_session():
        order = await get_order_by_id(session, order_id)
        if not order:
            from utils.keyboards import get_back_keyboard
            await callback.message.edit_text(
                "❌ Заказ не найден",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return
        
        from services.menu_service import get_menu_for_date
        menu_items = await get_menu_for_date(session, order.order_date)
        
        if not menu_items:
            from utils.keyboards import get_back_keyboard
            await callback.message.edit_text(
                "⚠️ Меню на эту дату недоступно",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return
        
        categories = {}
        for dish, menu_item in menu_items:
            if menu_item.available_quantity > 0:
                if dish.category not in categories:
                    categories[dish.category] = []
                categories[dish.category].append((dish, menu_item))
        
        if not categories:
            from utils.keyboards import get_back_keyboard
            await callback.message.edit_text(
                "😔 Нет доступных блюд",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return
        
        keyboard_buttons = []
        for category, items in categories.items():
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"📁 {category} ({len(items)})",
                callback_data=f"category_for_order_{order_id}_{category}"
            )])
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"edit_order_{order_id}")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
            "Выберите категорию для добавления:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("category_for_order_"))
async def callback_category_for_order(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    order_id = int(parts[3])
    category = "_".join(parts[4:])
    
    async for session in get_session():
        order = await get_order_by_id(session, order_id)
        from services.menu_service import get_menu_for_date
        menu_items = await get_menu_for_date(session, order.order_date)
        category_items = [(dish, menu) for dish, menu in menu_items 
                         if dish.category == category and menu.available_quantity > 0]
        
        if not category_items:
            from utils.keyboards import get_back_keyboard
            await callback.message.edit_text(
                "😔 В этой категории нет доступных блюд",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return
        
        keyboard_buttons = []
        for dish, menu_item in category_items:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"{dish.name} - {dish.price:.0f} ₽ (осталось: {menu_item.available_quantity})",
                callback_data=f"select_dish_order_{order_id}_{dish.id}"
            )])
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"add_to_order_{order_id}")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
            f"📁 {category}\n\nВыберите блюдо:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("select_dish_order_"))
async def callback_select_dish_order(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    order_id = int(parts[3])
    dish_id = int(parts[4])
    
    async for session in get_session():
        dish = await get_dish_by_id(session, dish_id)
        order = await get_order_by_id(session, order_id)
        menu_item = await get_menu_item(session, order.order_date, dish_id)
        
        if not dish or not menu_item or menu_item.available_quantity < 1:
            from utils.keyboards import get_back_keyboard
            await callback.message.edit_text(
                "❌ Блюдо недоступно",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return
        
        await state.update_data(order_id=order_id, dish_id=dish_id, dish_price=dish.price, quantity=1)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➖", callback_data="qty_order_-1"), 
             InlineKeyboardButton(text="1", callback_data="qty_order_1"),
             InlineKeyboardButton(text="➕", callback_data="qty_order_+1")],
            [InlineKeyboardButton(text="✅ Добавить", callback_data=f"confirm_add_order_{order_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"add_to_order_{order_id}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        await callback.message.edit_text(
            f"🍽️ {dish.name}\n\n"
            f"💰 Цена: {dish.price:.0f} ₽\n"
            f"Доступно: {menu_item.available_quantity} порций\n\n"
            f"Количество: 1",
            reply_markup=keyboard
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("qty_order_"))
async def callback_change_qty_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_qty = data.get("quantity", 1)
    
    if callback.data == "qty_order_+1":
        new_qty = min(current_qty + 1, 10)
    elif callback.data == "qty_order_-1":
        new_qty = max(current_qty - 1, 1)
    else:
        new_qty = int(callback.data.split("_")[-1])
    
    await state.update_data(quantity=new_qty)
    
    order_id = data.get("order_id")
    dish_id = data.get("dish_id")
    
    async for session in get_session():
        dish = await get_dish_by_id(session, dish_id)
        order = await get_order_by_id(session, order_id)
        menu_item = await get_menu_item(session, order.order_date, dish_id)
        total = dish.price * new_qty
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➖", callback_data="qty_order_-1"), 
             InlineKeyboardButton(text=str(new_qty), callback_data="qty_order_1"),
             InlineKeyboardButton(text="➕", callback_data="qty_order_+1")],
            [InlineKeyboardButton(text="✅ Добавить", callback_data=f"confirm_add_order_{order_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"add_to_order_{order_id}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        await callback.message.edit_text(
            f"🍽️ {dish.name}\n\n"
            f"💰 Цена: {dish.price:.0f} ₽\n"
            f"Доступно: {menu_item.available_quantity} порций\n\n"
            f"Количество: {new_qty}\n"
            f"Итого: {total:.0f} ₽",
            reply_markup=keyboard
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("confirm_add_order_"))
async def callback_confirm_add_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")
    dish_id = data.get("dish_id")
    quantity = data.get("quantity", 1)
    price = data.get("dish_price")
    
    async for session in get_session():
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.full_name
        )
        
        order = await get_order_by_id(session, order_id, user.id)
        menu_item = await get_menu_item(session, order.order_date, dish_id)
        
        if menu_item.available_quantity < quantity:
            await callback.answer(f"Доступно только {menu_item.available_quantity} порций", show_alert=True)
            return
        
        success = await add_item_to_order(session, order_id, user.id, dish_id, quantity, price)
        
        if success:
            menu_item.available_quantity -= quantity
            await session.commit()
            
            order = await get_order_by_id(session, order_id, user.id)
            items_text = "\n".join([
                f"{i+1}. {item.dish.name} x{item.quantity} - {item.price * item.quantity:.0f} ₽"
                for i, item in enumerate(order.items)
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить блюдо", callback_data=f"add_to_order_{order.id}")],
                *[[InlineKeyboardButton(
                    text=f"❌ Удалить: {item.dish.name}",
                    callback_data=f"remove_item_{order.id}_{item.id}"
                )] for item in order.items],
                [InlineKeyboardButton(text="✅ Сохранить", callback_data=f"save_order_{order.id}")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"order_details_{order.id}")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ])
            
            await callback.message.edit_text(
                f"✏️ Редактирование заказа #{order.id}\n\n"
                f"Дата: {format_date(order.order_date)}\n\n"
                f"Текущие позиции:\n{items_text}\n\n"
                f"Итого: {order.total_amount:.0f} ₽",
                reply_markup=keyboard
            )
            await callback.answer("Блюдо добавлено")
            await state.clear()
        else:
            from utils.keyboards import get_back_keyboard
            await callback.message.edit_text(
                "❌ Не удалось добавить блюдо",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()

@router.callback_query(lambda c: c.data.startswith("save_order_"))
async def callback_save_order(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.replace("save_order_", ""))
    
    async for session in get_session():
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.full_name
        )
        
        order = await get_order_by_id(session, order_id, user.id)
        
        if not order.items:
            from utils.keyboards import get_back_keyboard
            await callback.message.edit_text(
                "⚠️ Заказ не может быть пустым. Добавьте хотя бы одно блюдо.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Добавить блюдо", callback_data=f"add_to_order_{order_id}")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
            await callback.answer()
            return
        
        order_text = format_order(order)
        
        await callback.message.edit_text(
            f"✅ Заказ обновлен!\n\n{order_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ])
        )
        await callback.answer("Заказ сохранен")
        await state.clear()













