from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.database import get_session
from services.user_service import get_or_create_user
from services.order_service import get_user_orders, get_order_by_id, cancel_order, search_user_orders_by_dish
from models.order import OrderStatus
from utils.formatters import format_order, format_date
from datetime import datetime, timedelta

router = Router()

class HistoryFilterStates(StatesGroup):
    waiting_for_date_from = State()
    waiting_for_date_to = State()
    waiting_for_dish_search = State()

@router.message(Command("orders"))
async def cmd_orders(message: Message):
    async for session in get_session():
        user = await get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name
        )
        
        orders = await get_user_orders(session, user.id, OrderStatus.PENDING)
        
        if not orders:
            from utils.keyboards import get_main_menu_keyboard
            from services.user_service import is_admin
            user_is_admin = await is_admin(session, user.telegram_id)
            
            await message.answer(
                "📭 <b>Активных заказов нет</b>\n\n"
                "💡 Используйте кнопку '📋 Создать заказ' для оформления нового заказа.",
                reply_markup=get_main_menu_keyboard(is_admin=user_is_admin),
                parse_mode="HTML"
            )
            return
        
        for order in orders:
            order_text = format_order(order)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"cancel_order_{order.id}")],
                [InlineKeyboardButton(text="📋 Детали", callback_data=f"order_details_{order.id}")]
            ])
            await message.answer(
                order_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

@router.callback_query(lambda c: c.data == "my_orders")
async def callback_my_orders(callback: CallbackQuery):
    async for session in get_session():
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.full_name
        )
        
        orders = await get_user_orders(session, user.id, OrderStatus.PENDING)
        
        if not orders:
            from utils.keyboards import get_main_menu_keyboard
            from services.user_service import is_admin
            user_is_admin = await is_admin(session, user.telegram_id)
            
            await callback.message.edit_text(
                "📭 <b>Активных заказов нет</b>\n\n"
                "💡 Используйте кнопку '📋 Создать заказ' для оформления нового заказа.",
                reply_markup=get_main_menu_keyboard(is_admin=user_is_admin),
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        if len(orders) == 1:
            order = orders[0]
            order_text = format_order(order)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"cancel_order_{order.id}")],
                [InlineKeyboardButton(text="✏️ Редактировать заказ", callback_data=f"edit_order_{order.id}")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ])
            await callback.message.edit_text(
                order_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            keyboard_buttons = []
            for order in orders:
                keyboard_buttons.append([InlineKeyboardButton(
                    text=f"Заказ #{order.id} - {format_date(order.order_date)}",
                    callback_data=f"order_details_{order.id}"
                )])
            keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
            
            await callback.message.edit_text(
                f"Ваши активные заказы ({len(orders)}):",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("order_details_"))
async def callback_order_details(callback: CallbackQuery):
    order_id = int(callback.data.replace("order_details_", ""))
    
    async for session in get_session():
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.full_name
        )
        
        order = await get_order_by_id(session, order_id, user.id)
        
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        order_text = format_order(order)
        
        keyboard_buttons = []
        if order.status == OrderStatus.PENDING:
            keyboard_buttons.append([InlineKeyboardButton(text="✏️ Редактировать заказ", callback_data=f"edit_order_{order.id}")])
        keyboard_buttons.append([InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"cancel_order_{order.id}")])
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_orders")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
            order_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
            parse_mode="HTML"
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("cancel_order_"))
async def callback_cancel_order(callback: CallbackQuery):
    order_id = int(callback.data.replace("cancel_order_", ""))
    
    async for session in get_session():
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.full_name
        )
        
        order = await get_order_by_id(session, order_id, user.id)
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        from utils.validators import validate_order_can_be_cancelled
        can_cancel, error_msg = validate_order_can_be_cancelled(order.order_date)
        if not can_cancel:
            await callback.answer(error_msg, show_alert=True)
            return
        
        success = await cancel_order(session, order_id, user.id)
        
        if success:
            await callback.message.edit_text(
                f"✅ Заказ #{order_id} успешно отменен",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="my_orders")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
            await callback.answer("Заказ отменен")
        else:
            await callback.answer("Не удалось отменить заказ", show_alert=True)

@router.callback_query(lambda c: c.data == "order_history" or c.data.startswith("history_page_") or c.data == "history_clear_filters")
async def callback_order_history(callback: CallbackQuery, state: FSMContext):
    page = 0
    if callback.data.startswith("history_page_"):
        page = int(callback.data.replace("history_page_", ""))
    
    if callback.data == "history_clear_filters":
        await state.update_data(history_date_from=None, history_date_to=None, history_dish_search=None)
    
    ITEMS_PER_PAGE = 5
    filter_data = await state.get_data()
    date_from = filter_data.get("history_date_from")
    date_to = filter_data.get("history_date_to")
    dish_search = filter_data.get("history_dish_search")
    
    async for session in get_session():
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.full_name
        )
        
        # Применяем фильтры
        if dish_search:
            all_orders = await search_user_orders_by_dish(session, user.id, dish_search)
        else:
            all_orders = await get_user_orders(
                session, 
                user.id, 
                date_from=date_from, 
                date_to=date_to
            )
        
        completed_orders = [o for o in all_orders if o.status != OrderStatus.PENDING]
        
        if not completed_orders:
            filter_text = ""
            if date_from or date_to or dish_search:
                filter_text = "\n\n🔍 Активные фильтры:\n"
                if date_from:
                    filter_text += f"С: {format_date(date_from)}\n"
                if date_to:
                    filter_text += f"По: {format_date(date_to)}\n"
                if dish_search:
                    filter_text += f"Блюдо: {dish_search}\n"
            
            await callback.message.edit_text(
                f"История заказов пуста{filter_text}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔍 Фильтры", callback_data="history_filters")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
            await callback.answer()
            return
        
        total_pages = (len(completed_orders) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        if page >= total_pages:
            page = total_pages - 1
        if page < 0:
            page = 0
        
        start_idx = page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_orders = completed_orders[start_idx:end_idx]
        
        orders_text = "\n\n".join([
            f"Заказ #{order.id} - {format_date(order.order_date)}\n"
            f"Статус: {order.status.value}\n"
            f"Сумма: {order.total_amount:.0f} ₽"
            for order in page_orders
        ])
        
        filter_text = ""
        if date_from or date_to or dish_search:
            filter_text = "\n\n🔍 Фильтры: "
            filters = []
            if date_from:
                filters.append(f"с {format_date(date_from)}")
            if date_to:
                filters.append(f"по {format_date(date_to)}")
            if dish_search:
                filters.append(f'"{dish_search}"')
            filter_text += ", ".join(filters)
        
        keyboard_buttons = []
        
        # Кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◀️ Предыдущая", callback_data=f"history_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Следующая ▶️", callback_data=f"history_page_{page + 1}"))
        
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        keyboard_buttons.append([InlineKeyboardButton(text="🔍 Фильтры", callback_data="history_filters")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
            f"📊 История заказов (страница {page + 1} из {total_pages}){filter_text}:\n\n{orders_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )
        await callback.answer()

@router.callback_query(lambda c: c.data == "history_filters")
async def callback_history_filters(callback: CallbackQuery, state: FSMContext):
    filter_data = await state.get_data()
    date_from = filter_data.get("history_date_from")
    date_to = filter_data.get("history_date_to")
    dish_search = filter_data.get("history_dish_search")
    
    filter_info = "Текущие фильтры:\n"
    if date_from:
        filter_info += f"📅 С: {format_date(date_from)}\n"
    if date_to:
        filter_info += f"📅 По: {format_date(date_to)}\n"
    if dish_search:
        filter_info += f"🍽️ Блюдо: {dish_search}\n"
    if not date_from and not date_to and not dish_search:
        filter_info += "Нет активных фильтров\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Фильтр по дате (от)", callback_data="history_filter_date_from")],
        [InlineKeyboardButton(text="📅 Фильтр по дате (до)", callback_data="history_filter_date_to")],
        [InlineKeyboardButton(text="🍽️ Поиск по блюду", callback_data="history_filter_dish")],
        [InlineKeyboardButton(text="🗑️ Очистить фильтры", callback_data="history_clear_filters")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="order_history")]
    ])
    
    await callback.message.edit_text(
        f"🔍 Фильтры истории заказов\n\n{filter_info}",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "history_filter_date_from")
async def callback_history_filter_date_from(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HistoryFilterStates.waiting_for_date_from)
    await callback.message.edit_text(
        "📅 Введите дату начала периода (формат: ДД.ММ.ГГГГ или ДД-ММ-ГГГГ)\n"
        "Например: 01.12.2024\n\n"
        "Или отправьте '-' для отмены:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="order_history")]
        ])
    )
    await callback.answer()

@router.message(HistoryFilterStates.waiting_for_date_from)
async def process_history_date_from(message: Message, state: FSMContext):
    if message.text.strip() == "-":
        await state.update_data(history_date_from=None)
        from utils.keyboards import get_back_keyboard
        await message.answer(
            "✅ Фильтр по дате начала отменен",
            reply_markup=get_back_keyboard(back_callback="order_history", text="◀️ К истории заказов")
        )
        await state.clear()
        return
    
    try:
        # Пробуем разные форматы
        for fmt in ["%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d"]:
            try:
                date = datetime.strptime(message.text.strip(), fmt)
                date = date.replace(hour=0, minute=0, second=0, microsecond=0)
                await state.update_data(history_date_from=date)
                await message.answer(f"✅ Дата начала установлена: {format_date(date)}")
                await state.clear()
                return
            except ValueError:
                continue
        await message.answer("Неверный формат даты. Используйте ДД.ММ.ГГГГ (например: 01.12.2024)")
    except Exception as e:
        await message.answer(f"Ошибка при обработке даты: {str(e)}")

@router.callback_query(lambda c: c.data == "history_filter_date_to")
async def callback_history_filter_date_to(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HistoryFilterStates.waiting_for_date_to)
    await callback.message.edit_text(
        "📅 Введите дату окончания периода (формат: ДД.ММ.ГГГГ или ДД-ММ-ГГГГ)\n"
        "Например: 31.12.2024\n\n"
        "Или отправьте '-' для отмены:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="order_history")]
        ])
    )
    await callback.answer()

@router.message(HistoryFilterStates.waiting_for_date_to)
async def process_history_date_to(message: Message, state: FSMContext):
    if message.text.strip() == "-":
        await state.update_data(history_date_to=None)
        from utils.keyboards import get_back_keyboard
        await message.answer(
            "✅ Фильтр по дате окончания отменен",
            reply_markup=get_back_keyboard(back_callback="order_history", text="◀️ К истории заказов")
        )
        await state.clear()
        return
    
    try:
        # Пробуем разные форматы
        for fmt in ["%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d"]:
            try:
                date = datetime.strptime(message.text.strip(), fmt)
                date = date.replace(hour=23, minute=59, second=59, microsecond=999999)
                await state.update_data(history_date_to=date)
                await message.answer(f"✅ Дата окончания установлена: {format_date(date)}")
                await state.clear()
                return
            except ValueError:
                continue
        await message.answer("Неверный формат даты. Используйте ДД.ММ.ГГГГ (например: 31.12.2024)")
    except Exception as e:
        await message.answer(f"Ошибка при обработке даты: {str(e)}")

@router.callback_query(lambda c: c.data == "history_filter_dish")
async def callback_history_filter_dish(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HistoryFilterStates.waiting_for_dish_search)
    await callback.message.edit_text(
        "🍽️ Введите название блюда для поиска (можно частично)\n\n"
        "Или отправьте '-' для отмены:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="order_history")]
        ])
    )
    await callback.answer()

@router.message(HistoryFilterStates.waiting_for_dish_search)
async def process_history_dish_search(message: Message, state: FSMContext):
    if message.text.strip() == "-":
        await state.update_data(history_dish_search=None)
        from utils.keyboards import get_back_keyboard
        await message.answer(
            "✅ Поиск по блюду отменен",
            reply_markup=get_back_keyboard(back_callback="order_history", text="◀️ К истории заказов")
        )
        await state.clear()
        return
    
    search_term = message.text.strip()
    if len(search_term) < 2:
        from utils.keyboards import get_cancel_keyboard
        await message.answer(
            "⚠️ Введите хотя бы 2 символа для поиска",
            reply_markup=get_cancel_keyboard(cancel_callback="order_history")
        )
        return
    
    await state.update_data(history_dish_search=search_term)
    from utils.keyboards import get_back_keyboard
    await message.answer(
        f"✅ Поиск по блюду установлен: '{search_term}'",
        reply_markup=get_back_keyboard(back_callback="order_history", text="◀️ К истории заказов")
    )
    await state.clear()

