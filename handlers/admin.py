from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from database.database import get_session
from services.user_service import get_or_create_user, is_admin, get_all_users, get_user_by_id, update_user_office
from services.order_service import get_all_orders, get_order_by_id
from services.menu_service import get_menu_for_date
from services.report_service import get_orders_summary, get_dish_statistics, get_user_statistics, get_cafe_report
from services.menu_management_service import add_dish, update_dish, delete_dish, get_all_dishes, get_dish_by_id
from services.office_service import get_all_offices, get_office_by_id
from services.cafe_service import get_all_cafes
from models.order import OrderStatus
from utils.formatters import format_date
from utils.health_check import check_system_health, get_system_info
from utils.decorators import admin_required
from loguru import logger
import re

router = Router()

class DishManagementStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_category = State()
    editing_dish = State()
    editing_name = State()
    editing_description = State()
    editing_price = State()
    editing_category = State()
    editing_availability = State()

class AdminOrderFilterStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_search = State()
    waiting_for_keyword_search = State()

class LoadMenuStates(StatesGroup):
    waiting_for_date = State()
    selecting_dishes = State()
    setting_quantities = State()

class UserManagementStates(StatesGroup):
    waiting_for_telegram_id = State()
    waiting_for_full_name = State()
    waiting_for_office_selection = State()

async def check_admin(callback: CallbackQuery) -> bool:
    async for session in get_session():
        if not await is_admin(session, callback.from_user.id):
            await callback.answer("У вас нет прав администратора", show_alert=True)
            return False
    return True

@router.message(Command("admin"))
@admin_required
async def cmd_admin(message: Message):
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Все заказы", callback_data="admin_all_orders")],
            [InlineKeyboardButton(text="📊 Заказы на сегодня", callback_data="admin_today_orders")],
            [InlineKeyboardButton(text="📈 Отчеты и статистика", callback_data="admin_reports")],
            [InlineKeyboardButton(text="🍽️ Управление меню", callback_data="admin_menu")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="start")]
        ])
        
        await message.answer("⚙️ Админ-панель", reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "admin_panel")
async def callback_admin_panel(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Все заказы", callback_data="admin_all_orders")],
        [InlineKeyboardButton(text="📊 Заказы на сегодня", callback_data="admin_today_orders")],
        [InlineKeyboardButton(text="📈 Отчеты и статистика", callback_data="admin_reports")],
        [InlineKeyboardButton(text="🍽️ Управление меню", callback_data="admin_menu")],
        [InlineKeyboardButton(text="👥 Управление сотрудниками", callback_data="admin_users")],
        [InlineKeyboardButton(text="🏢 Управление офисами и кафе", callback_data="admin_offices_cafes")],
        [InlineKeyboardButton(text="⏰ Управление дедлайнами", callback_data="admin_deadlines")],
        [InlineKeyboardButton(text="🔍 Статус системы", callback_data="admin_health")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
    ])
    
    await callback.message.edit_text("⚙️ Админ-панель", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_users")
async def callback_admin_users(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Загрузить сотрудника", callback_data="admin_add_user")],
        [InlineKeyboardButton(text="📋 Список сотрудников", callback_data="admin_list_users")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
    ])
    
    await callback.message.edit_text(
        "👥 <b>Управление сотрудниками</b>\n\n"
        "💡 Выберите действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_all_orders" or c.data.startswith("admin_orders_filter_"))
async def callback_admin_all_orders(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик просмотра всех заказов в админ-панели
    Поддерживает фильтрацию по пользователю, статусу и поиск по ключевым словам
    """
    if not await check_admin(callback):
        return
    
    # Обработка фильтров
    filter_data = await state.get_data()
    user_id = filter_data.get("admin_orders_user_id")
    status_filter = filter_data.get("admin_orders_status")
    search_term = filter_data.get("admin_orders_search")
    
    if callback.data.startswith("admin_orders_filter_"):
        filter_type = callback.data.replace("admin_orders_filter_", "")
        if filter_type == "user":
            await callback_admin_orders_filter_user(callback, state)
            return
        elif filter_type == "status":
            await callback_admin_orders_filter_status(callback, state)
            return
        elif filter_type == "search":
            await callback_admin_orders_filter_search(callback, state)
            return
        elif filter_type == "clear":
            await state.update_data(admin_orders_user_id=None, admin_orders_status=None, admin_orders_search=None)
            await callback.answer("Фильтры очищены")
    
    async for session in get_session():
        orders = await get_all_orders(session, user_id=user_id, status=status_filter, search_term=search_term)
        
        if not orders:
            filter_text = ""
            if user_id or status_filter or search_term:
                filter_text = "\n\n🔍 Активные фильтры:\n"
                if user_id:
                    user = await get_user_by_id(session, user_id)
                    if user:
                        filter_text += f"Пользователь: {user.full_name or user.username or user.telegram_id}\n"
                if status_filter:
                    filter_text += f"Статус: {status_filter.value}\n"
                if search_term:
                    filter_text += f"Поиск: {search_term}\n"
            
            await callback.message.edit_text(
                f"Заказов нет{filter_text}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔍 Фильтры", callback_data="admin_orders_filters_menu")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
            await callback.answer()
            return
        
        orders_text = "\n\n".join([
            f"Заказ #{order.id}\n"
            f"Пользователь: {order.user.full_name or order.user.username or order.user.telegram_id}\n"
            f"Дата: {format_date(order.order_date)}\n"
            f"Статус: {order.status.value}\n"
            f"Сумма: {order.total_amount:.0f} ₽"
            for order in orders[:10]
        ])
        
        # Добавляем кнопки для каждого заказа (первые 10)
        order_buttons = []
        for order in orders[:10]:
            order_buttons.append([InlineKeyboardButton(
                text=f"Заказ #{order.id} - {order.user.full_name or order.user.username}",
                callback_data=f"admin_order_{order.id}"
            )])
        
        filter_text = ""
        if user_id or status_filter or search_term:
            filter_text = "\n\n🔍 Фильтры: "
            filters = []
            if user_id:
                user = await get_user_by_id(session, user_id)
                if user:
                    filters.append(f"Пользователь: {user.full_name or user.username}")
            if status_filter:
                filters.append(f"Статус: {status_filter.value}")
            if search_term:
                filters.append(f'Поиск: "{search_term}"')
            filter_text += ", ".join(filters)
        
        keyboard_buttons = order_buttons if order_buttons else []
        if len(orders) > 10:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"Показано 10 из {len(orders)}",
                callback_data="admin_orders_filters_menu"
            )])
        if len(orders) > 0:
            keyboard_buttons.append([InlineKeyboardButton(text="⚙️ Массовые операции", callback_data="admin_bulk_operations")])
        keyboard_buttons.append([InlineKeyboardButton(text="🔍 Фильтры", callback_data="admin_orders_filters_menu")])
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
            f"📋 Все заказы ({len(orders)}){filter_text}:\n\n{orders_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )
        await callback.answer()

@router.callback_query(lambda c: c.data == "admin_orders_filters_menu")
async def callback_admin_orders_filters_menu(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    filter_data = await state.get_data()
    user_id = filter_data.get("admin_orders_user_id")
    status_filter = filter_data.get("admin_orders_status")
    search_term = filter_data.get("admin_orders_search")
    
    filter_info = "Текущие фильтры:\n"
    async for session in get_session():
        if user_id:
            user = await get_user_by_id(session, user_id)
            if user:
                filter_info += f"👤 Пользователь: {user.full_name or user.username or user.telegram_id}\n"
        if status_filter:
            filter_info += f"📊 Статус: {status_filter.value}\n"
        if search_term:
            filter_info += f"🔍 Поиск: {search_term}\n"
        if not user_id and not status_filter and not search_term:
            filter_info += "Нет активных фильтров\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Фильтр по пользователю", callback_data="admin_orders_filter_user")],
        [InlineKeyboardButton(text="📊 Фильтр по статусу", callback_data="admin_orders_filter_status")],
        [InlineKeyboardButton(text="🔍 Поиск по ключевым словам", callback_data="admin_orders_filter_search")],
        [InlineKeyboardButton(text="🗑️ Очистить фильтры", callback_data="admin_orders_filter_clear")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_all_orders")]
    ])
    
    await callback.message.edit_text(
        f"🔍 Фильтры заказов\n\n{filter_info}",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_orders_filter_user" or c.data.startswith("admin_users_page_"))
async def callback_admin_orders_filter_user(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    page = 0
    if callback.data.startswith("admin_users_page_"):
        page = int(callback.data.replace("admin_users_page_", ""))
    
    USERS_PER_PAGE = 15
    
    async for session in get_session():
        users = await get_all_users(session)
        
        if not users:
            await callback.answer("Пользователей нет", show_alert=True)
            return
        
        total_pages = (len(users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE
        if page >= total_pages:
            page = total_pages - 1
        if page < 0:
            page = 0
        
        start_idx = page * USERS_PER_PAGE
        end_idx = start_idx + USERS_PER_PAGE
        page_users = users[start_idx:end_idx]
        
        keyboard_buttons = []
        for user in page_users:
            user_name = user.full_name or user.username or f"ID: {user.telegram_id}"
            keyboard_buttons.append([InlineKeyboardButton(
                text=user_name,
                callback_data=f"admin_filter_user_{user.id}"
            )])
        
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◀️ Предыдущая", callback_data=f"admin_users_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Следующая ▶️", callback_data=f"admin_users_page_{page + 1}"))
        
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        keyboard_buttons.append([InlineKeyboardButton(text="❌ Сбросить фильтр", callback_data="admin_filter_user_clear")])
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_orders_filters_menu")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
            f"👤 Выберите пользователя для фильтрации (страница {page + 1} из {total_pages}):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("admin_filter_user_"))
async def callback_admin_filter_user_select(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    user_id_str = callback.data.replace("admin_filter_user_", "")
    
    if user_id_str == "clear":
        await state.update_data(admin_orders_user_id=None)
        await callback.answer("Фильтр по пользователю сброшен")
    else:
        user_id = int(user_id_str)
        await state.update_data(admin_orders_user_id=user_id)
        await callback.answer("Фильтр по пользователю установлен")
    
    # Возвращаемся к списку заказов
    await callback_admin_all_orders(callback, state)

@router.callback_query(lambda c: c.data == "admin_orders_filter_status")
async def callback_admin_orders_filter_status(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ В ожидании", callback_data="admin_filter_status_PENDING")],
        [InlineKeyboardButton(text="✅ Подтвержден", callback_data="admin_filter_status_CONFIRMED")],
        [InlineKeyboardButton(text="❌ Отменен", callback_data="admin_filter_status_CANCELLED")],
        [InlineKeyboardButton(text="✅ Завершен", callback_data="admin_filter_status_COMPLETED")],
        [InlineKeyboardButton(text="❌ Сбросить фильтр", callback_data="admin_filter_status_clear")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_orders_filters_menu")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
    ])
    
    await callback.message.edit_text(
        "📊 Выберите статус для фильтрации:",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("admin_filter_status_"))
async def callback_admin_filter_status_select(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    status_str = callback.data.replace("admin_filter_status_", "")
    
    if status_str == "clear":
        await state.update_data(admin_orders_status=None)
        await callback.answer("Фильтр по статусу сброшен")
    else:
        status = OrderStatus[status_str]
        await state.update_data(admin_orders_status=status)
        await callback.answer(f"Фильтр по статусу установлен: {status.value}")
    
    # Возвращаемся к списку заказов
    await callback_admin_all_orders(callback, state)

@router.callback_query(lambda c: c.data.startswith("admin_order_") and not c.data.startswith("admin_order_status_") and not c.data.startswith("admin_edit_order_") and not c.data.startswith("admin_add_order_item_"))
async def callback_admin_order_details(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    order_id = int(callback.data.replace("admin_order_", ""))
    
    async for session in get_session():
        # Загружаем заказ с загрузкой всех связанных объектов
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        from models.order import Order, OrderItem
        
        query = select(Order).options(
            selectinload(Order.items).selectinload(OrderItem.dish),
            selectinload(Order.user)
        ).where(Order.id == order_id)
        
        result = await session.execute(query)
        order = result.scalar_one_or_none()
        
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        from utils.formatters import format_order
        order_text = format_order(order)
        
        keyboard_buttons = []
        
        if order.status != OrderStatus.PENDING:
            keyboard_buttons.append([InlineKeyboardButton(
                text="⏳ Вернуть в ожидание",
                callback_data=f"admin_order_status_{order.id}_PENDING"
            )])
        if order.status != OrderStatus.CONFIRMED:
            keyboard_buttons.append([InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"admin_order_status_{order.id}_CONFIRMED"
            )])
        if order.status != OrderStatus.COMPLETED:
            keyboard_buttons.append([InlineKeyboardButton(
                text="✅ Завершить",
                callback_data=f"admin_order_status_{order.id}_COMPLETED"
            )])
        if order.status != OrderStatus.CANCELLED:
            keyboard_buttons.append([InlineKeyboardButton(
                text="❌ Отменить",
                callback_data=f"admin_order_status_{order.id}_CANCELLED"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="✏️ Редактировать заказ", callback_data=f"admin_edit_order_{order.id}")])
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_all_orders")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
            f"📋 <b>Детали заказа</b>\n\n"
            f"{order_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
            parse_mode="HTML"
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("admin_order_status_"))
async def callback_admin_order_status_change(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    parts = callback.data.replace("admin_order_status_", "").split("_")
    order_id = int(parts[0])
    new_status_str = parts[1]
    
    try:
        new_status = OrderStatus[new_status_str]
    except KeyError:
        await callback.answer("Неверный статус", show_alert=True)
        return
    
    async for session in get_session():
        from services.order_service import update_order_status
        order = await update_order_status(session, order_id, new_status)
        
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        status_names = {
            OrderStatus.PENDING: "⏳ В ожидании",
            OrderStatus.CONFIRMED: "✅ Подтвержден",
            OrderStatus.COMPLETED: "✅ Завершен",
            OrderStatus.CANCELLED: "❌ Отменен"
        }
        
        from services.notification_service import notify_user_about_order_status
        from config.bot_instance import get_bot
        
        bot = get_bot()
        notification = (
            f"📦 Изменение статуса заказа\n\n"
            f"Заказ #{order.id}\n"
            f"Новый статус: {status_names[new_status]}\n"
            f"Дата заказа: {format_date(order.order_date)}"
        )
        await notify_user_about_order_status(bot, order.user.telegram_id, notification)
        
        await callback.answer(f"Статус изменен на: {status_names[new_status]}")
        
        await callback_admin_order_details(callback)

@router.callback_query(lambda c: c.data.startswith("admin_edit_order_"))
async def callback_admin_edit_order(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    order_id = int(callback.data.replace("admin_edit_order_", ""))
    
    async for session in get_session():
        order = await get_order_by_id(session, order_id)
        
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        from utils.formatters import format_order
        order_text = format_order(order)
        
        keyboard_buttons = []
        
        for item in order.items:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"✏️ {item.dish.name} x{item.quantity}",
                callback_data=f"admin_edit_order_item_{order.id}_{item.id}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="➕ Добавить блюдо", callback_data=f"admin_add_order_item_{order.id}")])
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_order_{order.id}")])
        
        await callback.message.edit_text(
            f"✏️ Редактирование заказа #{order.id}\n\n{order_text}\n\nВыберите позицию для редактирования:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )
        await callback.answer()

@router.callback_query(lambda c: c.data == "admin_today_orders")
async def callback_admin_today_orders(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    async for session in get_session():
        orders = await get_all_orders(session, today)
        
        if not orders:
            await callback.message.edit_text(
                "📭 На сегодня заказов нет",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
            await callback.answer()
            return
        
        total_amount = sum(order.total_amount for order in orders)
        total_items = sum(sum(item.quantity for item in order.items) for order in orders)
        
        # Добавляем кнопки для каждого заказа
        keyboard_buttons = []
        for order in orders:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"📦 Заказ #{order.id} - {order.user.full_name or order.user.username}",
                callback_data=f"admin_order_{order.id}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        orders_text = "\n".join([
            f"  • Заказ #{order.id} - {order.user.full_name or order.user.username} - {order.total_amount:.0f} ₽"
            for order in orders
        ])
        
        await callback.message.edit_text(
            f"📊 <b>Заказы на сегодня</b>\n\n"
            f"📦 Всего заказов: <b>{len(orders)}</b>\n"
            f"🍽️ Всего позиций: <b>{total_items}</b>\n"
            f"💰 Общая сумма: <b>{total_amount:.0f} ₽</b>\n\n"
            f"📋 <b>Список заказов:</b>\n"
            f"{orders_text}\n\n"
            f"💡 Нажмите на заказ для просмотра деталей",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
            parse_mode="HTML"
        )
        await callback.answer()

@router.callback_query(lambda c: c.data == "admin_reports")
async def callback_admin_reports(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Сводка на сегодня", callback_data="report_today")],
        [InlineKeyboardButton(text="☕ Отчеты по кафе", callback_data="report_cafe")],
        [InlineKeyboardButton(text="🍽️ Статистика по блюдам", callback_data="report_dishes")],
        [InlineKeyboardButton(text="👥 Статистика по пользователям", callback_data="report_users")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
    ])
    
    await callback.message.edit_text("📈 Отчеты и статистика", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(lambda c: c.data == "report_today")
async def callback_report_today(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    async for session in get_session():
        summary = await get_orders_summary(session, today)
        
        report_text = (
            f"📊 Сводка заказов на {format_date(today)}:\n\n"
            f"Всего заказов: {summary['total_orders']}\n"
            f"Уникальных пользователей: {summary['unique_users']}\n"
            f"Общая сумма: {summary['total_amount']:.0f} ₽"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 Экспорт в Excel", callback_data="export_today")],
            [InlineKeyboardButton(text="📄 Экспорт в CSV", callback_data="export_today_csv")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_reports")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        await callback.message.edit_text(
            report_text,
            reply_markup=keyboard
        )
        await callback.answer()

@router.callback_query(lambda c: c.data == "report_dishes")
async def callback_report_dishes(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    async for session in get_session():
        stats = await get_dish_statistics(session, today)
        
        if not stats:
            await callback.message.edit_text(
                "На сегодня нет статистики по блюдам",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_reports")]
                ])
            )
            await callback.answer()
            return
        
        stats_text = "🍽️ Топ блюд на сегодня:\n\n"
        for i, stat in enumerate(stats[:10], 1):
            stats_text += (
                f"{i}. {stat['name']}\n"
                f"   Количество: {stat['quantity']} порций\n"
                f"   Выручка: {stat['revenue']:.0f} ₽\n\n"
            )
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_reports")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ])
        )
        await callback.answer()

@router.callback_query(lambda c: c.data == "report_users")
async def callback_report_users(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    async for session in get_session():
        stats = await get_user_statistics(session, today)
        
        if not stats:
            await callback.message.edit_text(
                "На сегодня нет статистики по пользователям",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_reports")]
                ])
            )
            await callback.answer()
            return
        
        stats_text = "👥 Топ пользователей на сегодня:\n\n"
        for i, stat in enumerate(stats[:10], 1):
            stats_text += (
                f"{i}. {stat['name']}\n"
                f"   Заказов: {stat['orders_count']}\n"
                f"   Сумма: {stat['total_amount']:.0f} ₽\n"
                f"   Средний чек: {stat['avg_order']:.0f} ₽\n\n"
            )
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_reports")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ])
        )
        await callback.answer()

@router.callback_query(lambda c: c.data == "admin_menu")
async def callback_admin_menu(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить блюдо", callback_data="admin_add_dish")],
        [InlineKeyboardButton(text="📋 Список блюд", callback_data="admin_list_dishes")],
        [InlineKeyboardButton(text="📅 Загрузить меню на дату", callback_data="admin_load_menu")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
    ])
    
    await callback.message.edit_text(
        "🍽️ Управление меню",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_list_dishes")
async def callback_admin_list_dishes(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    async for session in get_session():
        dishes = await get_all_dishes(session)
        
        if not dishes:
            await callback.message.edit_text(
                "Блюд пока нет",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Добавить блюдо", callback_data="admin_add_dish")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
            await callback.answer()
            return
        
        categories = {}
        for dish in dishes:
            if dish.category not in categories:
                categories[dish.category] = []
            categories[dish.category].append(dish)
        
        keyboard_buttons = []
        for category, category_dishes in categories.items():
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"📁 {category} ({len(category_dishes)})",
                callback_data=f"admin_category_{category}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
            f"📋 Список блюд ({len(dishes)}):\n\nВыберите категорию:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("admin_category_"))
async def callback_admin_category_dishes(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    category = callback.data.replace("admin_category_", "")
    
    async for session in get_session():
        dishes = await get_all_dishes(session)
        category_dishes = [d for d in dishes if d.category == category]
        
        if not category_dishes:
            await callback.answer("В этой категории нет блюд", show_alert=True)
            return
        
        keyboard_buttons = []
        for dish in category_dishes:
            status = "✅" if dish.available else "❌"
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"{status} {dish.name} - {dish.price:.0f} ₽",
                callback_data=f"admin_dish_{dish.id}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_list_dishes")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
            f"📁 {category}\n\nВыберите блюдо для редактирования:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("admin_dish_"))
async def callback_admin_dish_details(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    dish_id = int(callback.data.replace("admin_dish_", ""))
    
    async for session in get_session():
        dish = await get_dish_by_id(session, dish_id)
        
        if not dish:
            await callback.answer("Блюдо не найдено", show_alert=True)
            return
        
        status = "✅ Доступно" if dish.available else "❌ Недоступно"
        dish_text = (
            f"🍽️ {dish.name}\n\n"
            f"📝 Описание: {dish.description or 'Нет описания'}\n"
            f"💰 Цена: {dish.price:.0f} ₽\n"
            f"📁 Категория: {dish.category}\n"
            f"📊 Статус: {status}\n"
            f"🆔 ID: {dish.id}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать название", callback_data=f"edit_dish_name_{dish.id}")],
            [InlineKeyboardButton(text="✏️ Редактировать описание", callback_data=f"edit_dish_desc_{dish.id}")],
            [InlineKeyboardButton(text="✏️ Редактировать цену", callback_data=f"edit_dish_price_{dish.id}")],
            [InlineKeyboardButton(text="✏️ Редактировать категорию", callback_data=f"edit_dish_category_{dish.id}")],
            [InlineKeyboardButton(
                text="🔄 Изменить доступность" if dish.available else "🔄 Сделать доступным",
                callback_data=f"toggle_dish_{dish.id}"
            )],
            [InlineKeyboardButton(text="🗑️ Удалить блюдо", callback_data=f"delete_dish_{dish.id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_list_dishes")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        await callback.message.edit_text(dish_text, reply_markup=keyboard)
        await callback.answer()

@router.callback_query(lambda c: c.data == "admin_load_menu")
async def callback_admin_load_menu(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    await state.set_state(LoadMenuStates.waiting_for_date)
    await callback.message.edit_text(
        "📅 Загрузка меню на дату\n\n"
        "Введите дату для загрузки меню (формат: ДД.ММ.ГГГГ)\n"
        "Например: 15.12.2024\n\n"
        "Или отправьте '-' для отмены:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
    )
    await callback.answer()

@router.message(LoadMenuStates.waiting_for_date)
async def process_load_menu_date(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
    
    if message.text.strip() == "-":
        await state.clear()
        await message.answer("Операция отменена")
        return
    
    try:
        # Пробуем разные форматы
        for fmt in ["%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d"]:
            try:
                date = datetime.strptime(message.text.strip(), fmt)
                date = date.replace(hour=0, minute=0, second=0, microsecond=0)
                await state.update_data(load_menu_date=date)
                
                # Получаем список всех блюд
                dishes = await get_all_dishes(session)
                
                if not dishes:
                    await message.answer(
                        "Нет доступных блюд. Сначала добавьте блюда в меню.",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")],
                            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                        ])
                    )
                    await state.clear()
                    return
                
                # Группируем по категориям
                categories = {}
                for dish in dishes:
                    if dish.category not in categories:
                        categories[dish.category] = []
                    categories[dish.category].append(dish)
                
                keyboard_buttons = []
                for category, category_dishes in categories.items():
                    keyboard_buttons.append([InlineKeyboardButton(
                        text=f"📁 {category} ({len(category_dishes)})",
                        callback_data=f"load_menu_category_{category}"
                    )])
                
                keyboard_buttons.append([InlineKeyboardButton(text="✅ Загрузить все блюда", callback_data="load_menu_all")])
                keyboard_buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")])
                keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
                
                await message.answer(
                    f"📅 Дата установлена: {format_date(date)}\n\n"
                    "Выберите категорию блюд для загрузки в меню:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
                )
                await state.set_state(LoadMenuStates.selecting_dishes)
                return
            except ValueError:
                continue
        await message.answer("Неверный формат даты. Используйте ДД.ММ.ГГГГ (например: 15.12.2024)")
    except Exception as e:
        await message.answer(f"Ошибка при обработке даты: {str(e)}")

@router.callback_query(lambda c: c.data.startswith("load_menu_category_") or c.data == "load_menu_all")
async def callback_load_menu_select_dishes(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    data = await state.get_data()
    menu_date = data.get("load_menu_date")
    
    if not menu_date:
        await callback.answer("Ошибка: дата не установлена", show_alert=True)
        return
    
    async for session in get_session():
        dishes = await get_all_dishes(session)
        
        selected_dishes = []
        if callback.data == "load_menu_all":
            selected_dishes = dishes
        else:
            category = callback.data.replace("load_menu_category_", "")
            selected_dishes = [d for d in dishes if d.category == category]
        
        if not selected_dishes:
            await callback.answer("Нет блюд для загрузки", show_alert=True)
            return
        
        # Сохраняем выбранные блюда
        await state.update_data(load_menu_dishes=[d.id for d in selected_dishes])
        await state.set_state(LoadMenuStates.setting_quantities)
        
        # Показываем список блюд и запрашиваем количество
        dishes_text = "\n".join([f"  • {d.name}" for d in selected_dishes])
        
        await callback.message.edit_text(
            f"📅 Дата: {format_date(menu_date)}\n\n"
            f"Выбранные блюда ({len(selected_dishes)}):\n{dishes_text}\n\n"
            "Введите количество для каждого блюда через запятую\n"
            "Например: 10, 15, 20\n"
            "Или одно число для всех блюд:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ])
        )
        await callback.answer()

@router.message(LoadMenuStates.setting_quantities)
async def process_load_menu_quantities(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
        
        data = await state.get_data()
        menu_date = data.get("load_menu_date")
        dish_ids = data.get("load_menu_dishes")
        
        if not menu_date or not dish_ids:
            await message.answer("Ошибка: данные не найдены")
            await state.clear()
            return
        
        try:
            quantities_input = message.text.strip()
            quantities = []
            
            # Парсим количество
            if "," in quantities_input:
                # Несколько значений
                quantities = [int(q.strip()) for q in quantities_input.split(",")]
            else:
                # Одно значение для всех
                qty = int(quantities_input)
                quantities = [qty] * len(dish_ids)
            
            # Проверяем количество значений
            if len(quantities) != len(dish_ids):
                await message.answer(
                    f"Количество значений ({len(quantities)}) не совпадает с количеством блюд ({len(dish_ids)}).\n"
                    "Введите правильное количество значений:"
                )
                return
            
            # Проверяем, что все значения положительные
            if any(q <= 0 for q in quantities):
                await message.answer("Количество должно быть положительным числом. Попробуйте снова:")
                return
            
            MAX_QUANTITY = 10000
            if any(q > MAX_QUANTITY for q in quantities):
                await message.answer(
                    f"Максимальное количество порций на блюдо: {MAX_QUANTITY}. "
                    "Попробуйте снова:"
                )
                return
            
            # Загружаем меню
            from services.menu_management_service import load_menu_for_date
            menus = await load_menu_for_date(session, menu_date, dish_ids, quantities)
            
            dishes = await get_all_dishes(session)
            dishes_dict = {d.id: d for d in dishes}
            
            loaded_text = "\n".join([
                f"  • {dishes_dict[did].name}: {qty} порций"
                for did, qty in zip(dish_ids, quantities)
            ])
            
            await message.answer(
                f"✅ Меню успешно загружено на {format_date(menu_date)}:\n\n{loaded_text}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📅 Загрузить еще", callback_data="admin_load_menu")],
                    [InlineKeyboardButton(text="◀️ К управлению меню", callback_data="admin_menu")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
            await state.clear()
        except ValueError:
            await message.answer("Неверный формат. Введите числа через запятую или одно число для всех блюд:")
        except Exception as e:
            await message.answer(f"Ошибка при загрузке меню: {str(e)}")
            await state.clear()

@router.callback_query(lambda c: c.data == "export_today")
async def callback_export_report(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    from config.bot_instance import get_bot
    from aiogram.types import ChatAction
    
    bot = get_bot()
    await bot.send_chat_action(callback.message.chat.id, ChatAction.TYPING)
    msg = await callback.message.answer("⏳ Генерация отчета...")
    
    async for session in get_session():
        from utils.export_service import export_statistics_to_excel
        from aiogram.types import BufferedInputFile
        
        summary = await get_orders_summary(session, today)
        dishes = await get_dish_statistics(session, today)
        users = await get_user_statistics(session, today)
        
        stats_data = {
            "summary": {
                "total_orders": summary["total_orders"],
                "unique_users": summary["unique_users"],
                "total_amount": summary["total_amount"]
            },
            "dishes": dishes,
            "users": users
        }
        
        excel_file = export_statistics_to_excel(stats_data)
        file = BufferedInputFile(excel_file.read(), filename=f"report_{today.strftime('%Y-%m-%d')}.xlsx")
        
        await msg.delete()
        await callback.message.answer_document(
            file,
            caption=f"📊 Отчет за {format_date(today)}"
        )
        await callback.answer("Отчет отправлен")

@router.callback_query(lambda c: c.data == "export_today_csv")
async def callback_export_report_csv(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    from config.bot_instance import get_bot
    from aiogram.types import ChatAction
    
    bot = get_bot()
    await bot.send_chat_action(callback.message.chat.id, ChatAction.TYPING)
    msg = await callback.message.answer("⏳ Генерация отчета...")
    
    async for session in get_session():
        from utils.export_service import export_statistics_to_csv
        from aiogram.types import BufferedInputFile
        
        summary = await get_orders_summary(session, today)
        dishes = await get_dish_statistics(session, today)
        users = await get_user_statistics(session, today)
        
        stats_data = {
            "summary": {
                "total_orders": summary["total_orders"],
                "unique_users": summary["unique_users"],
                "total_amount": summary["total_amount"]
            },
            "dishes": dishes,
            "users": users
        }
        
        csv_file = export_statistics_to_csv(stats_data)
        file = BufferedInputFile(csv_file.read(), filename=f"report_{today.strftime('%Y-%m-%d')}.csv")
        
        await msg.delete()
        await callback.message.answer_document(
            file,
            caption=f"📄 Отчет за {format_date(today)} (CSV)"
        )
        await callback.answer("Отчет отправлен")

# Добавление блюда
@router.callback_query(lambda c: c.data == "admin_add_dish")
async def callback_admin_add_dish(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    await state.set_state(DishManagementStates.waiting_for_name)
    await callback.message.edit_text(
        "➕ <b>Добавление нового блюда</b>\n\n"
        "📝 <b>Введите название блюда:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_dish_add")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "cancel_dish_add")
async def callback_cancel_dish_add(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Операция отменена",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
    )
    await callback.answer()

@router.message(DishManagementStates.waiting_for_name)
async def process_dish_name(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
    
    await state.update_data(name=message.text)
    await state.set_state(DishManagementStates.waiting_for_description)
    await message.answer(
        "\n"
        "   ✅ <b>Название принято</b>\n"
        "\n\n"
        f"📝 <b>Название:</b> {message.text}\n\n"
        "📄 <b>Введите описание блюда:</b>\n"
        "💡 <i>(или отправьте '-' для пропуска)</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_dish_add")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ]),
        parse_mode="HTML"
    )

@router.message(DishManagementStates.waiting_for_description)
async def process_dish_description(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
    
    description = message.text if message.text != "-" else None
    await state.update_data(description=description)
    await state.set_state(DishManagementStates.waiting_for_price)
    await message.answer(
        "✅ <b>Описание принято</b>\n\n"
        f"📄 <b>Описание:</b> {description or '<i>Не указано</i>'}\n\n"
        "💰 <b>Введите цену блюда:</b>\n"
        "💡 <i>Только число, например: 250</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_dish_add")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ]),
        parse_mode="HTML"
    )

@router.message(DishManagementStates.waiting_for_price)
async def process_dish_price(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
    
    try:
        price = float(message.text.replace(",", "."))
        if price <= 0:
            await message.answer(
                "❌ <b>Ошибка!</b>\n\n"
                "Цена должна быть положительным числом.\n"
                "Попробуйте снова:",
                parse_mode="HTML"
            )
            return
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат!</b>\n\n"
            "Введите число (например: 250):",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(price=price)
    await state.set_state(DishManagementStates.waiting_for_category)
    await message.answer(
        "\n"
        "   ✅ <b>Цена принята</b>\n"
        "\n\n"
        f"💰 <b>Цена:</b> {price:.0f} ₽\n\n"
        "📁 <b>Введите категорию блюда:</b>\n"
        "💡 <i>Например: Супы, Гарниры, Салаты, Горячее</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_dish_add")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ]),
        parse_mode="HTML"
    )

@router.message(DishManagementStates.waiting_for_category)
async def process_dish_category(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
    
    category = message.text.strip()
    if not category:
        await message.answer(
            "❌ <b>Ошибка!</b>\n\n"
            "Категория не может быть пустой.\n"
            "Введите категорию:",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    name = data.get("name")
    description = data.get("description")
    price = data.get("price")
    
    dish = await add_dish(session, name, description, price, category)
    
    await message.answer(
        f"\n"
        f"   ✅ <b>Блюдо успешно добавлено!</b>\n"
        f"\n\n"
        f"🍽️ <b>Название:</b> {dish.name}\n"
        f"📝 <b>Описание:</b> {dish.description or '<i>Нет описания</i>'}\n"
        f"💰 <b>Цена:</b> {dish.price:.0f} ₽\n"
        f"📁 <b>Категория:</b> {dish.category}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить еще", callback_data="admin_add_dish")],
            [InlineKeyboardButton(text="📋 Список блюд", callback_data="admin_list_dishes")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ]),
        parse_mode="HTML"
    )
    await state.clear()

# Редактирование блюда
@router.callback_query(lambda c: c.data.startswith("edit_dish_name_"))
async def callback_edit_dish_name(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    dish_id = int(callback.data.replace("edit_dish_name_", ""))
    await state.update_data(dish_id=dish_id, edit_field="name")
    await state.set_state(DishManagementStates.editing_name)
    
    await callback.message.edit_text(
        "Введите новое название блюда:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_dish_{dish_id}")]
        ])
    )
    await callback.answer()

@router.message(DishManagementStates.editing_name)
async def process_edit_dish_name(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
        
        data = await state.get_data()
        dish_id = data.get("dish_id")
        
        dish = await update_dish(session, dish_id, name=message.text)
        if dish:
            await message.answer(
                f"✅ Название блюда обновлено на '{dish.name}'",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К блюду", callback_data=f"admin_dish_{dish_id}")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
        else:
            await message.answer("Ошибка: блюдо не найдено", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ]))
        await state.clear()

@router.callback_query(lambda c: c.data.startswith("edit_dish_desc_"))
async def callback_edit_dish_desc(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    dish_id = int(callback.data.replace("edit_dish_desc_", ""))
    await state.update_data(dish_id=dish_id)
    await state.set_state(DishManagementStates.editing_description)
    
    await callback.message.edit_text(
        "Введите новое описание блюда (или отправьте '-' для удаления описания):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_dish_{dish_id}")]
        ])
    )
    await callback.answer()

@router.message(DishManagementStates.editing_description)
async def process_edit_dish_desc(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
        
        data = await state.get_data()
        dish_id = data.get("dish_id")
        description = message.text if message.text != "-" else None
        
        dish = await update_dish(session, dish_id, description=description)
        if dish:
            await message.answer(
                f"✅ Описание блюда обновлено",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К блюду", callback_data=f"admin_dish_{dish_id}")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
        else:
            await message.answer("Ошибка: блюдо не найдено", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ]))
        await state.clear()

@router.callback_query(lambda c: c.data.startswith("edit_dish_price_"))
async def callback_edit_dish_price(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    dish_id = int(callback.data.replace("edit_dish_price_", ""))
    await state.update_data(dish_id=dish_id)
    await state.set_state(DishManagementStates.editing_price)
    
    await callback.message.edit_text(
        "Введите новую цену блюда (только число):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_dish_{dish_id}")]
        ])
    )
    await callback.answer()

@router.message(DishManagementStates.editing_price)
async def process_edit_dish_price(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
        
        try:
            price = float(message.text.replace(",", "."))
            if price <= 0:
                await message.answer("Цена должна быть положительным числом. Попробуйте снова:")
                return
        except ValueError:
            await message.answer("Неверный формат цены. Введите число:")
            return
        
        data = await state.get_data()
        dish_id = data.get("dish_id")
        
        dish = await update_dish(session, dish_id, price=price)
        if dish:
            await message.answer(
                f"✅ Цена блюда обновлена на {dish.price:.0f} ₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К блюду", callback_data=f"admin_dish_{dish_id}")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
        else:
            await message.answer("Ошибка: блюдо не найдено", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ]))
        await state.clear()

@router.callback_query(lambda c: c.data.startswith("edit_dish_category_"))
async def callback_edit_dish_category(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    dish_id = int(callback.data.replace("edit_dish_category_", ""))
    await state.update_data(dish_id=dish_id)
    await state.set_state(DishManagementStates.editing_category)
    
    await callback.message.edit_text(
        "Введите новую категорию блюда:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_dish_{dish_id}")]
        ])
    )
    await callback.answer()

@router.message(DishManagementStates.editing_category)
async def process_edit_dish_category(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
        
        category = message.text.strip()
        if not category:
            await message.answer("Категория не может быть пустой. Введите категорию:")
            return
        
        data = await state.get_data()
        dish_id = data.get("dish_id")
        
        dish = await update_dish(session, dish_id, category=category)
        if dish:
            await message.answer(
                f"✅ Категория блюда обновлена на '{dish.category}'",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К блюду", callback_data=f"admin_dish_{dish_id}")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
        else:
            await message.answer("Ошибка: блюдо не найдено", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ]))
        await state.clear()

@router.callback_query(lambda c: c.data.startswith("toggle_dish_"))
async def callback_toggle_dish(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    dish_id = int(callback.data.replace("toggle_dish_", ""))
    
    async for session in get_session():
        dish = await get_dish_by_id(session, dish_id)
        if not dish:
            await callback.answer("Блюдо не найдено", show_alert=True)
            return
        
        new_availability = not dish.available
        dish = await update_dish(session, dish_id, available=new_availability)
        
        if dish:
            status = "доступно" if dish.available else "недоступно"
            await callback.answer(f"Блюдо теперь {status}")
            
            from services.notification_service import notify_users_about_menu_change
            from config.bot_instance import get_bot
            
            bot = get_bot()
            notification = f"🍽️ Изменение меню\n\nБлюдо '{dish.name}' теперь {status}"
            await notify_users_about_menu_change(bot, notification)
            
            # Обновляем сообщение с деталями блюда
            status_text = "✅ Доступно" if dish.available else "❌ Недоступно"
            dish_text = (
                f"🍽️ {dish.name}\n\n"
                f"📝 Описание: {dish.description or 'Нет описания'}\n"
                f"💰 Цена: {dish.price:.0f} ₽\n"
                f"📁 Категория: {dish.category}\n"
                f"📊 Статус: {status_text}\n"
                f"🆔 ID: {dish.id}"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Редактировать название", callback_data=f"edit_dish_name_{dish.id}")],
                [InlineKeyboardButton(text="✏️ Редактировать описание", callback_data=f"edit_dish_desc_{dish.id}")],
                [InlineKeyboardButton(text="✏️ Редактировать цену", callback_data=f"edit_dish_price_{dish.id}")],
                [InlineKeyboardButton(text="✏️ Редактировать категорию", callback_data=f"edit_dish_category_{dish.id}")],
                [InlineKeyboardButton(
                    text="🔄 Изменить доступность" if dish.available else "🔄 Сделать доступным",
                    callback_data=f"toggle_dish_{dish.id}"
                )],
                [InlineKeyboardButton(text="🗑️ Удалить блюдо", callback_data=f"delete_dish_{dish.id}")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_list_dishes")]
            ])
            
            await callback.message.edit_text(dish_text, reply_markup=keyboard)
        else:
            await callback.answer("Ошибка при обновлении", show_alert=True)

@router.callback_query(lambda c: c.data.startswith("delete_dish_") and not c.data.startswith("delete_dish_confirm_"))
async def callback_delete_dish(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    dish_id = int(callback.data.replace("delete_dish_", ""))
    
    async for session in get_session():
        dish = await get_dish_by_id(session, dish_id)
        if not dish:
            await callback.answer("Блюдо не найдено", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"⚠️ <b>Подтверждение удаления</b>\n\n"
            f"Вы уверены, что хотите удалить блюдо:\n"
            f"<b>{dish.name}</b>?\n\n"
            f"Это действие нельзя отменить!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_dish_confirm_{dish_id}")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_dish_{dish_id}")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("delete_dish_confirm_"))
async def callback_delete_dish_confirm(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    dish_id = int(callback.data.replace("delete_dish_confirm_", ""))
    
    async for session in get_session():
        dish = await get_dish_by_id(session, dish_id)
        if not dish:
            await callback.answer("Блюдо не найдено", show_alert=True)
            return
        
        dish_name = dish.name
        success = await delete_dish(session, dish_id)
        
        if success:
            from services.notification_service import notify_users_about_menu_change
            from config.bot_instance import get_bot
            
            bot = get_bot()
            notification = f"🍽️ Изменение меню\n\nБлюдо '{dish_name}' удалено из меню"
            await notify_users_about_menu_change(bot, notification)
            
            await callback.message.edit_text(
                f"✅ Блюдо '{dish_name}' успешно удалено",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К списку блюд", callback_data="admin_list_dishes")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
            await callback.answer("Блюдо удалено")
        else:
            await callback.answer("Ошибка при удалении", show_alert=True)

@router.callback_query(lambda c: c.data == "admin_health")
async def callback_admin_health(callback: CallbackQuery):
    """Проверка состояния системы"""
    if not await check_admin(callback):
        return
    
    health = await check_system_health()
    info = await get_system_info()
    
    status_emoji = "✅" if health["status"] == "healthy" else "❌"
    
    text = f"{status_emoji} Статус системы: {health['status']}\n\n"
    text += f"📊 Проверки:\n"
    for check_name, check_data in health["checks"].items():
        check_emoji = "✅" if check_data["status"] == "ok" else "❌"
        text += f"{check_emoji} {check_name}: {check_data['message']}\n"
    
    text += f"\n⚙️ Конфигурация:\n"
    text += f"• Токен бота: {'✅ Установлен' if info['bot_token_set'] else '❌ Не установлен'}\n"
    text += f"• Тип БД: {info['database_type']}\n"
    text += f"• Администраторов: {info['admin_count']}\n"
    text += f"• Дедлайн заказа: {info['order_deadline']}\n"
    text += f"• Ежедневный отчет: {info['daily_report_time']}\n"
    text += f"• Еженедельный отчет: {info['weekly_report']}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_health")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(lambda c: c.data == "export_cafe_excel")
async def callback_export_cafe_excel(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    from config.bot_instance import get_bot
    from aiogram.types import ChatAction, BufferedInputFile
    
    bot = get_bot()
    await bot.send_chat_action(callback.message.chat.id, ChatAction.TYPING)
    msg = await callback.message.answer("⏳ Генерация отчета...")
    
    async for session in get_session():
        cafe_report = await get_cafe_report(session, today)
        
        from utils.export_service import export_cafe_report_to_excel
        excel_file = export_cafe_report_to_excel(cafe_report)
        file = BufferedInputFile(excel_file.read(), filename=f"cafe_report_{today.strftime('%Y-%m-%d')}.xlsx")
        
        await msg.delete()
        await callback.message.answer_document(
            file,
            caption=f"📊 Отчет по кафе за {format_date(today)}"
        )
        await callback.answer("Отчет отправлен")

@router.callback_query(lambda c: c.data == "send_to_cafe")
async def callback_send_to_cafe(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    async for session in get_session():
        from services.report_service import get_cafe_report
        from services.cafe_service import get_all_cafes
        from config.bot_instance import get_bot
        
        cafe_report = await get_cafe_report(session, today)
        cafes = await get_all_cafes(session, active_only=True)
        
        if not cafe_report["cafes"]:
            await callback.answer("На сегодня нет заказов для отправки в кафе", show_alert=True)
            return
        
        bot = get_bot()
        
        sent_count = 0
        for cafe_data in cafe_report["cafes"]:
            if cafe_data["total_orders"] == 0:
                continue
            
            cafe_report_text = (
                f"📋 <b>Заказы на {today.strftime('%d.%m.%Y')}</b>\n\n"
                f"☕ <b>Кафе:</b> {cafe_data['cafe_name']}\n\n"
                f"📦 Всего заказов: <b>{cafe_data['total_orders']}</b>\n"
                f"👥 Сотрудников: <b>{cafe_data['unique_users']}</b>\n"
                f"🍽️ Всего позиций: <b>{cafe_data['total_items']}</b>\n"
                f"💰 Общая сумма: <b>{cafe_data['total_amount']:.0f} ₽</b>\n\n"
                f"📋 <b>Детали заказов:</b>\n\n"
            )
            
            for i, order_detail in enumerate(cafe_data["orders"], 1):
                cafe_report_text += (
                    f"<b>{i}. {order_detail['user_name']}</b>\n"
                    f"   📱 ID: {order_detail['telegram_id']}\n"
                    f"   🍽️ {order_detail['items']}\n"
                )
                if order_detail.get('delivery_time'):
                    cafe_report_text += f"   ⏰ {order_detail['delivery_time']}\n"
                cafe_report_text += f"   💰 {order_detail['total']:.0f} ₽\n\n"
            
            try:
                await bot.send_message(
                    callback.message.chat.id,
                    cafe_report_text,
                    parse_mode="HTML"
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Ошибка при отправке отчета для кафе {cafe_data['cafe_name']}: {e}")
        
        if sent_count > 0:
            await callback.answer(
                f"✅ Отчеты по {sent_count} кафе отправлены!\n\n"
                "💡 Скопируйте текст и отправьте в каждое кафе вручную или используйте экспорт в Excel.",
                show_alert=True
            )
        else:
            await callback.answer("Не удалось отправить отчеты", show_alert=True)

@router.callback_query(lambda c: c.data == "admin_offices_cafes")
async def callback_admin_offices_cafes(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 Управление офисами", callback_data="admin_offices")],
        [InlineKeyboardButton(text="☕ Управление кафе", callback_data="admin_cafes")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
    ])
    
    await callback.message.edit_text(
        "🏢 <b>Управление офисами и кафе</b>\n\n"
        "💡 Выберите действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_offices")
async def callback_admin_offices(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    async for session in get_session():
        from services.office_service import get_all_offices
        offices = await get_all_offices(session, active_only=False)
        
        keyboard_buttons = []
        for office in offices:
            status = "✅" if office.is_active else "❌"
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"{status} {office.name}",
                callback_data=f"admin_office_{office.id}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="➕ Добавить офис", callback_data="admin_add_office")])
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_offices_cafes")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
            f"🏢 Управление офисами\n\nВсего офисов: {len(offices)}\n\nВыберите офис для редактирования:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )
        await callback.answer()

@router.callback_query(lambda c: c.data == "admin_cafes")
async def callback_admin_cafes(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    async for session in get_session():
        cafes = await get_all_cafes(session, active_only=False)
        
        keyboard_buttons = []
        for cafe in cafes:
            status = "✅" if cafe.is_active else "❌"
            office_name = cafe.office.name if cafe.office else "Без офиса"
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"{status} {cafe.name} ({office_name})",
                callback_data=f"admin_cafe_{cafe.id}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="➕ Добавить кафе", callback_data="admin_add_cafe")])
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_offices_cafes")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
            f"☕ Управление кафе\n\nВсего кафе: {len(cafes)}\n\nВыберите кафе для редактирования:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )
        await callback.answer()

@router.callback_query(lambda c: c.data == "admin_deadlines")
async def callback_admin_deadlines(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    async for session in get_session():
        from services.deadline_service import get_all_deadlines
        deadlines = await get_all_deadlines(session, active_only=False)
        
        keyboard_buttons = []
        for deadline in deadlines[:20]:
            status = "✅" if deadline.is_active else "❌"
            date_str = deadline.date.strftime("%d.%m.%Y")
            time_str = deadline.deadline_time.strftime("%H:%M")
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"{status} {date_str} {time_str}",
                callback_data=f"admin_deadline_{deadline.id}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="➕ Добавить дедлайн", callback_data="admin_add_deadline")])
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
            f"⏰ Управление дедлайнами\n\nВсего дедлайнов: {len(deadlines)}\n\nВыберите дедлайн для редактирования:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )
        await callback.answer()

@router.callback_query(lambda c: c.data == "admin_add_user")
async def callback_admin_add_user(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    await state.set_state(UserManagementStates.waiting_for_telegram_id)
    await callback.message.edit_text(
        "➕ <b>Загрузка сотрудника</b>\n\n"
        "📱 <b>Введите Telegram ID сотрудника:</b>\n"
        "💡 Можно узнать у @userinfobot",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_users")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(UserManagementStates.waiting_for_telegram_id)
async def process_user_telegram_id(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
    
    try:
        telegram_id = int(message.text.strip())
        await state.update_data(telegram_id=telegram_id)
        await state.set_state(UserManagementStates.waiting_for_full_name)
        await message.answer(
            f"✅ Telegram ID принят: {telegram_id}\n\n"
            "👤 <b>Введите полное имя сотрудника:</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_users")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ])
        )
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число (Telegram ID):")

@router.message(UserManagementStates.waiting_for_full_name)
async def process_user_full_name(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
        
        data = await state.get_data()
        telegram_id = data.get("telegram_id")
        full_name = message.text.strip()
        
        await state.update_data(full_name=full_name)
        await state.set_state(UserManagementStates.waiting_for_office_selection)
        
        from services.office_service import get_all_offices
        offices = await get_all_offices(session)
        
        keyboard_buttons = []
        for office in offices:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"🏢 {office.name}",
                callback_data=f"select_user_office_{office.id}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="⏭️ Пропустить (без офиса)", callback_data="select_user_office_skip")])
        keyboard_buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_users")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await message.answer(
            f"✅ Имя принято: {full_name}\n\n"
            "🏢 <b>Выберите офис сотрудника:</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )

@router.callback_query(lambda c: c.data.startswith("select_user_office_"))
async def callback_select_user_office(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    office_id_str = callback.data.replace("select_user_office_", "")
    
    async for session in get_session():
        data = await state.get_data()
        telegram_id = data.get("telegram_id")
        full_name = data.get("full_name")
        
        office_id = None
        if office_id_str != "skip":
            office_id = int(office_id_str)
        
        from services.user_service import get_or_create_user, update_user_office
        user = await get_or_create_user(session, telegram_id, None, full_name)
        
        if office_id:
            await update_user_office(session, user.id, office_id)
            office = await get_office_by_id(session, office_id)
            office_name = office.name if office else ""
            await callback.message.edit_text(
                f"✅ <b>Сотрудник успешно добавлен!</b>\n\n"
                f"👤 <b>Имя:</b> {full_name}\n"
                f"📱 <b>Telegram ID:</b> {telegram_id}\n"
                f"🏢 <b>Офис:</b> {office_name}",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Добавить еще", callback_data="admin_add_user")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
        else:
            await callback.message.edit_text(
                f"✅ <b>Сотрудник успешно добавлен!</b>\n\n"
                f"👤 <b>Имя:</b> {full_name}\n"
                f"📱 <b>Telegram ID:</b> {telegram_id}\n"
                f"🏢 <b>Офис:</b> Не указан",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Добавить еще", callback_data="admin_add_user")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
        
        await state.clear()
        await callback.answer()

@router.callback_query(lambda c: c.data == "admin_list_users")
async def callback_admin_list_users(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    async for session in get_session():
        users = await get_all_users(session)
        
        if not users:
            await callback.message.edit_text(
                "Сотрудников пока нет",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Загрузить сотрудника", callback_data="admin_add_user")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
            await callback.answer()
            return
        
        keyboard_buttons = []
        for user in users[:20]:
            office_name = user.office.name if user.office else "Без офиса"
            user_name = user.full_name or user.username or f"ID: {user.telegram_id}"
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"👤 {user_name} ({office_name})",
                callback_data=f"admin_user_{user.id}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await callback.message.edit_text(
            f"👥 Список сотрудников\n\nВсего сотрудников: {len(users)}\n\nВыберите сотрудника для просмотра:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("report_cafe"))
async def callback_report_cafe(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    async for session in get_session():
        from services.report_service import get_cafe_report
        cafe_report = await get_cafe_report(session, today)
        
        if not cafe_report["cafes"]:
            await callback.message.edit_text(
                f"📊 Отчет по кафе на {format_date(today)}\n\n"
                "На сегодня заказов нет.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_reports")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
            await callback.answer()
            return
        
        report_text = f"📊 <b>Отчет по кафе на {format_date(today)}</b>\n\n"
        report_text += f"Всего заказов: {cafe_report['total_orders']}\n"
        report_text += f"Общая сумма: {cafe_report['total_amount']:.0f} ₽\n\n"
        
        for cafe_data in cafe_report["cafes"]:
            report_text += f"\n☕ <b>{cafe_data['cafe_name']}</b>\n\n"
            report_text += f"📦 Заказов: {cafe_data['total_orders']}\n"
            report_text += f"👥 Сотрудников: {cafe_data['unique_users']}\n"
            report_text += f"💰 Сумма: {cafe_data['total_amount']:.0f} ₽\n\n"
            
            for order_detail in cafe_data["orders"]:
                report_text += f"  • <b>{order_detail['user_name']}</b>\n"
                report_text += f"    {order_detail['items']}\n"
                if order_detail['delivery_time']:
                    report_text += f"    ⏰ {order_detail['delivery_time']}\n"
                report_text += f"    💰 {order_detail['total']:.0f} ₽\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 Экспорт в Excel", callback_data="export_cafe_excel")],
            [InlineKeyboardButton(text="📧 Отправить в кафе", callback_data="send_to_cafe")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_reports")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        if len(report_text) > 4096:
            parts = [report_text[i:i+4096] for i in range(0, len(report_text), 4096)]
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    await callback.message.edit_text(part, reply_markup=keyboard, parse_mode="HTML")
                else:
                    await callback.message.answer(part, parse_mode="HTML")
        else:
            await callback.message.edit_text(report_text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

class OfficeManagementStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()

class CafeManagementStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_office_selection = State()
    waiting_for_contact_info = State()

class DeadlineManagementStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_office_cafe_selection = State()

@router.callback_query(lambda c: c.data == "admin_add_office")
async def callback_admin_add_office(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    await state.set_state(OfficeManagementStates.waiting_for_name)
    await callback.message.edit_text(
        "➕ <b>Добавление офиса</b>\n\n"
        "📝 <b>Введите название офиса:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_offices")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(OfficeManagementStates.waiting_for_name)
async def process_office_name(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
    
    office_name = message.text.strip()
    if not office_name:
        await message.answer("❌ Название офиса не может быть пустым. Попробуйте снова:")
        return
    
    await state.update_data(office_name=office_name)
    await state.set_state(OfficeManagementStates.waiting_for_address)
    await message.answer(
        f"✅ Название принято: {office_name}\n\n"
        "📍 <b>Введите адрес офиса:</b>\n"
        "💡 <i>(или отправьте '-' для пропуска)</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_offices")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
    )

@router.message(OfficeManagementStates.waiting_for_address)
async def process_office_address(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
        
        data = await state.get_data()
        office_name = data.get("office_name")
        address = message.text.strip() if message.text.strip() != "-" else None
        
        from services.office_service import create_office
        office = await create_office(session, office_name, address)
        
        await message.answer(
            f"✅ <b>Офис успешно добавлен!</b>\n\n"
            f"🏢 <b>Название:</b> {office.name}\n"
            f"📍 <b>Адрес:</b> {office.address or 'Не указан'}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить еще", callback_data="admin_add_office")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_offices")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ])
        )
        await state.clear()

@router.callback_query(lambda c: c.data.startswith("admin_office_"))
async def callback_admin_office_details(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    office_id = int(callback.data.replace("admin_office_", ""))
    
    async for session in get_session():
        office = await get_office_by_id(session, office_id)
        
        if not office:
            await callback.answer("Офис не найден", show_alert=True)
            return
        
        status = "✅ Активен" if office.is_active else "❌ Неактивен"
        office_text = (
            f"🏢 <b>{office.name}</b>\n\n"
            f"📍 <b>Адрес:</b> {office.address or 'Не указан'}\n"
            f"📊 <b>Статус:</b> {status}\n"
            f"🆔 <b>ID:</b> {office.id}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔄 Деактивировать" if office.is_active else "🔄 Активировать",
                callback_data=f"toggle_office_{office.id}"
            )],
            [InlineKeyboardButton(text="🗑️ Удалить офис", callback_data=f"delete_office_{office.id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_offices")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        await callback.message.edit_text(office_text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("toggle_office_"))
async def callback_toggle_office(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    office_id = int(callback.data.replace("toggle_office_", ""))
    
    async for session in get_session():
        from services.office_service import get_office_by_id, update_office
        office = await get_office_by_id(session, office_id)
        
        if not office:
            await callback.answer("Офис не найден", show_alert=True)
            return
        
        new_status = not office.is_active
        office = await update_office(session, office_id, is_active=new_status)
        
        status = "активирован" if new_status else "деактивирован"
        await callback.answer(f"Офис {status}")
        await callback_admin_office_details(callback)

@router.callback_query(lambda c: c.data.startswith("delete_office_") and not c.data.startswith("delete_office_confirm_"))
async def callback_delete_office(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    office_id = int(callback.data.replace("delete_office_", ""))
    
    async for session in get_session():
        office = await get_office_by_id(session, office_id)
        
        if not office:
            await callback.answer("Офис не найден", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"⚠️ <b>Подтверждение удаления</b>\n\n"
            f"Вы уверены, что хотите удалить офис:\n"
            f"<b>{office.name}</b>?\n\n"
            f"Это действие нельзя отменить!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_office_confirm_{office_id}")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_office_{office_id}")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("delete_office_confirm_"))
async def callback_delete_office_confirm(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    office_id = int(callback.data.replace("delete_office_confirm_", ""))
    
    async for session in get_session():
        from services.office_service import get_office_by_id, delete_office
        office = await get_office_by_id(session, office_id)
        
        if not office:
            await callback.answer("Офис не найден", show_alert=True)
            return
        
        office_name = office.name
        success = await delete_office(session, office_id)
        
        if success:
            await callback.message.edit_text(
                f"✅ Офис '{office_name}' успешно удален",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К списку офисов", callback_data="admin_offices")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
            await callback.answer("Офис удален")
        else:
            await callback.answer("Ошибка при удалении", show_alert=True)

@router.callback_query(lambda c: c.data == "admin_add_cafe")
async def callback_admin_add_cafe(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    await state.set_state(CafeManagementStates.waiting_for_name)
    await callback.message.edit_text(
        "➕ <b>Добавление кафе</b>\n\n"
        "📝 <b>Введите название кафе:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cafes")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(CafeManagementStates.waiting_for_name)
async def process_cafe_name(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
    
    cafe_name = message.text.strip()
    if not cafe_name:
        await message.answer("❌ Название кафе не может быть пустым. Попробуйте снова:")
        return
    
    await state.update_data(cafe_name=cafe_name)
    await state.set_state(CafeManagementStates.waiting_for_office_selection)
    
    async for session in get_session():
        offices = await get_all_offices(session)
        
        keyboard_buttons = []
        for office in offices:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"🏢 {office.name}",
                callback_data=f"select_cafe_office_{office.id}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="⏭️ Пропустить (без офиса)", callback_data="select_cafe_office_skip")])
        keyboard_buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cafes")])
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
        
        await message.answer(
            f"✅ Название принято: {cafe_name}\n\n"
            "🏢 <b>Выберите офис для кафе:</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )

@router.callback_query(lambda c: c.data.startswith("select_cafe_office_"))
async def callback_select_cafe_office(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    office_id_str = callback.data.replace("select_cafe_office_", "")
    
    async for session in get_session():
        data = await state.get_data()
        cafe_name = data.get("cafe_name")
        
        office_id = None
        if office_id_str != "skip":
            office_id = int(office_id_str)
            await state.update_data(office_id=office_id)
        
        await state.set_state(CafeManagementStates.waiting_for_contact_info)
        await callback.message.edit_text(
            f"✅ Офис выбран\n\n"
            f"📝 <b>Название:</b> {cafe_name}\n\n"
            "📞 <b>Введите контактную информацию кафе:</b>\n"
            "💡 <i>(телефон, email или отправьте '-' для пропуска)</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cafes")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ])
        )
        await callback.answer()

@router.message(CafeManagementStates.waiting_for_contact_info)
async def process_cafe_contact_info(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
        
        data = await state.get_data()
        cafe_name = data.get("cafe_name")
        office_id = data.get("office_id")
        contact_info = message.text.strip() if message.text.strip() != "-" else None
        
        from services.cafe_service import create_cafe
        cafe = await create_cafe(session, cafe_name, office_id, contact_info)
        
        office_name = ""
        if office_id:
            office = await get_office_by_id(session, office_id)
            office_name = office.name if office else ""
        
        await message.answer(
            f"✅ <b>Кафе успешно добавлено!</b>\n\n"
            f"☕ <b>Название:</b> {cafe.name}\n"
            f"🏢 <b>Офис:</b> {office_name or 'Не указан'}\n"
            f"📞 <b>Контакты:</b> {cafe.contact_info or 'Не указаны'}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить еще", callback_data="admin_add_cafe")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_cafes")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ])
        )
        await state.clear()

@router.callback_query(lambda c: c.data.startswith("admin_cafe_"))
async def callback_admin_cafe_details(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    cafe_id = int(callback.data.replace("admin_cafe_", ""))
    
    async for session in get_session():
        from services.cafe_service import get_cafe_by_id
        cafe = await get_cafe_by_id(session, cafe_id)
        
        if not cafe:
            await callback.answer("Кафе не найдено", show_alert=True)
            return
        
        status = "✅ Активно" if cafe.is_active else "❌ Неактивно"
        office_name = cafe.office.name if cafe.office else "Без офиса"
        cafe_text = (
            f"☕ <b>{cafe.name}</b>\n\n"
            f"🏢 <b>Офис:</b> {office_name}\n"
            f"📞 <b>Контакты:</b> {cafe.contact_info or 'Не указаны'}\n"
            f"📊 <b>Статус:</b> {status}\n"
            f"🆔 <b>ID:</b> {cafe.id}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔄 Деактивировать" if cafe.is_active else "🔄 Активировать",
                callback_data=f"toggle_cafe_{cafe.id}"
            )],
            [InlineKeyboardButton(text="🗑️ Удалить кафе", callback_data=f"delete_cafe_{cafe.id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_cafes")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        await callback.message.edit_text(cafe_text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("toggle_cafe_"))
async def callback_toggle_cafe(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    cafe_id = int(callback.data.replace("toggle_cafe_", ""))
    
    async for session in get_session():
        from services.cafe_service import get_cafe_by_id, update_cafe
        cafe = await get_cafe_by_id(session, cafe_id)
        
        if not cafe:
            await callback.answer("Кафе не найдено", show_alert=True)
            return
        
        new_status = not cafe.is_active
        cafe = await update_cafe(session, cafe_id, is_active=new_status)
        
        status = "активировано" if new_status else "деактивировано"
        await callback.answer(f"Кафе {status}")
        await callback_admin_cafe_details(callback)

@router.callback_query(lambda c: c.data.startswith("delete_cafe_") and not c.data.startswith("delete_cafe_confirm_"))
async def callback_delete_cafe(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    cafe_id = int(callback.data.replace("delete_cafe_", ""))
    
    async for session in get_session():
        from services.cafe_service import get_cafe_by_id
        cafe = await get_cafe_by_id(session, cafe_id)
        
        if not cafe:
            await callback.answer("Кафе не найдено", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"⚠️ <b>Подтверждение удаления</b>\n\n"
            f"Вы уверены, что хотите удалить кафе:\n"
            f"<b>{cafe.name}</b>?\n\n"
            f"Это действие нельзя отменить!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_cafe_confirm_{cafe_id}")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_cafe_{cafe_id}")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("delete_cafe_confirm_"))
async def callback_delete_cafe_confirm(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    cafe_id = int(callback.data.replace("delete_cafe_confirm_", ""))
    
    async for session in get_session():
        from services.cafe_service import get_cafe_by_id, delete_cafe
        cafe = await get_cafe_by_id(session, cafe_id)
        
        if not cafe:
            await callback.answer("Кафе не найдено", show_alert=True)
            return
        
        cafe_name = cafe.name
        success = await delete_cafe(session, cafe_id)
        
        if success:
            await callback.message.edit_text(
                f"✅ Кафе '{cafe_name}' успешно удалено",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К списку кафе", callback_data="admin_cafes")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
            await callback.answer("Кафе удалено")
        else:
            await callback.answer("Ошибка при удалении", show_alert=True)

@router.callback_query(lambda c: c.data == "admin_add_deadline")
async def callback_admin_add_deadline(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    await state.set_state(DeadlineManagementStates.waiting_for_date)
    await callback.message.edit_text(
        "➕ <b>Добавление дедлайна</b>\n\n"
        "📅 <b>Введите дату дедлайна (формат: ДД.ММ.ГГГГ):</b>\n"
        "Например: 15.12.2024",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_deadlines")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(DeadlineManagementStates.waiting_for_date)
async def process_deadline_date(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
    
    try:
        for fmt in ["%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d"]:
            try:
                date = datetime.strptime(message.text.strip(), fmt)
                date = date.replace(hour=0, minute=0, second=0, microsecond=0)
                await state.update_data(deadline_date=date)
                await state.set_state(DeadlineManagementStates.waiting_for_time)
                await message.answer(
                    f"✅ Дата принята: {format_date(date)}\n\n"
                    "⏰ <b>Введите время дедлайна (формат: ЧЧ:ММ):</b>\n"
                    "Например: 12:00",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_deadlines")],
                        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                    ])
                )
                return
            except ValueError:
                continue
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ (например: 15.12.2024)")
    except Exception as e:
        await message.answer(f"Ошибка при обработке даты: {str(e)}")

@router.message(DeadlineManagementStates.waiting_for_time)
async def process_deadline_time(message: Message, state: FSMContext):
    async for session in get_session():
        if not await is_admin(session, message.from_user.id):
            await message.answer("У вас нет прав администратора")
            return
        
        try:
            time_str = message.text.strip()
            time_obj = datetime.strptime(time_str, "%H:%M").time()
            
            data = await state.get_data()
            deadline_date = data.get("deadline_date")
            deadline_datetime = datetime.combine(deadline_date.date(), time_obj)
            
            await state.update_data(deadline_time=deadline_datetime)
            await state.set_state(DeadlineManagementStates.waiting_for_office_cafe_selection)
            
            offices = await get_all_offices(session)
            cafes = await get_all_cafes(session, active_only=False)
            
            keyboard_buttons = []
            keyboard_buttons.append([InlineKeyboardButton(text="🏢 Для всех офисов", callback_data="deadline_scope_all_offices")])
            for office in offices:
                keyboard_buttons.append([InlineKeyboardButton(
                    text=f"🏢 {office.name}",
                    callback_data=f"deadline_scope_office_{office.id}"
                )])
            
            keyboard_buttons.append([InlineKeyboardButton(text="☕ Для всех кафе", callback_data="deadline_scope_all_cafes")])
            for cafe in cafes:
                keyboard_buttons.append([InlineKeyboardButton(
                    text=f"☕ {cafe.name}",
                    callback_data=f"deadline_scope_cafe_{cafe.id}"
                )])
            
            keyboard_buttons.append([InlineKeyboardButton(text="⏭️ Без привязки", callback_data="deadline_scope_none")])
            keyboard_buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_deadlines")])
            keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")])
            
            await message.answer(
                f"✅ Время принято: {time_str}\n\n"
                "🏢 <b>Выберите область действия дедлайна:</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            )
        except ValueError:
            await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ (например: 12:00)")

@router.callback_query(lambda c: c.data.startswith("deadline_scope_"))
async def callback_deadline_scope(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        return
    
    scope = callback.data.replace("deadline_scope_", "")
    
    async for session in get_session():
        data = await state.get_data()
        deadline_date = data.get("deadline_date")
        deadline_time = data.get("deadline_time")
        
        office_id = None
        cafe_id = None
        
        if scope.startswith("office_"):
            office_id = int(scope.replace("office_", ""))
        elif scope.startswith("cafe_"):
            cafe_id = int(scope.replace("cafe_", ""))
        elif scope == "all_offices":
            pass
        elif scope == "all_cafes":
            pass
        
        from services.deadline_service import create_deadline
        deadline = await create_deadline(session, deadline_date, deadline_time, office_id, cafe_id)
        
        scope_text = ""
        if office_id:
            office = await get_office_by_id(session, office_id)
            scope_text = f"Офис: {office.name if office else ''}"
        elif cafe_id:
            from services.cafe_service import get_cafe_by_id
            cafe = await get_cafe_by_id(session, cafe_id)
            scope_text = f"Кафе: {cafe.name if cafe else ''}"
        elif scope == "all_offices":
            scope_text = "Для всех офисов"
        elif scope == "all_cafes":
            scope_text = "Для всех кафе"
        else:
            scope_text = "Без привязки"
        
        await callback.message.edit_text(
            f"✅ <b>Дедлайн успешно добавлен!</b>\n\n"
            f"📅 <b>Дата:</b> {format_date(deadline_date)}\n"
            f"⏰ <b>Время:</b> {deadline_time.strftime('%H:%M')}\n"
            f"🎯 <b>Область:</b> {scope_text}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить еще", callback_data="admin_add_deadline")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_deadlines")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
            ])
        )
        await state.clear()
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("admin_deadline_"))
async def callback_admin_deadline_details(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    deadline_id = int(callback.data.replace("admin_deadline_", ""))
    
    async for session in get_session():
        from services.deadline_service import get_all_deadlines
        deadlines = await get_all_deadlines(session, active_only=False)
        deadline = next((d for d in deadlines if d.id == deadline_id), None)
        
        if not deadline:
            await callback.answer("Дедлайн не найден", show_alert=True)
            return
        
        status = "✅ Активен" if deadline.is_active else "❌ Неактивен"
        scope_text = ""
        if deadline.office_id:
            office = await get_office_by_id(session, deadline.office_id)
            scope_text = f"Офис: {office.name if office else ''}"
        elif deadline.cafe_id:
            from services.cafe_service import get_cafe_by_id
            cafe = await get_cafe_by_id(session, deadline.cafe_id)
            scope_text = f"Кафе: {cafe.name if cafe else ''}"
        else:
            scope_text = "Без привязки"
        
        deadline_text = (
            f"⏰ <b>Дедлайн</b>\n\n"
            f"📅 <b>Дата:</b> {format_date(deadline.date)}\n"
            f"🕐 <b>Время:</b> {deadline.deadline_time.strftime('%H:%M')}\n"
            f"🎯 <b>Область:</b> {scope_text}\n"
            f"📊 <b>Статус:</b> {status}\n"
            f"🆔 <b>ID:</b> {deadline.id}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔄 Деактивировать" if deadline.is_active else "🔄 Активировать",
                callback_data=f"toggle_deadline_{deadline.id}"
            )],
            [InlineKeyboardButton(text="🗑️ Удалить дедлайн", callback_data=f"delete_deadline_{deadline.id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_deadlines")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        await callback.message.edit_text(deadline_text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("toggle_deadline_"))
async def callback_toggle_deadline(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    deadline_id = int(callback.data.replace("toggle_deadline_", ""))
    
    async for session in get_session():
        from services.deadline_service import update_deadline
        deadline = await update_deadline(session, deadline_id, is_active=None)
        
        if not deadline:
            await callback.answer("Дедлайн не найден", show_alert=True)
            return
        
        new_status = not deadline.is_active
        deadline = await update_deadline(session, deadline_id, is_active=new_status)
        
        status = "активирован" if new_status else "деактивирован"
        await callback.answer(f"Дедлайн {status}")
        await callback_admin_deadline_details(callback)

@router.callback_query(lambda c: c.data.startswith("delete_deadline_") and not c.data.startswith("delete_deadline_confirm_"))
async def callback_delete_deadline(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    deadline_id = int(callback.data.replace("delete_deadline_", ""))
    
    async for session in get_session():
        from services.deadline_service import get_all_deadlines
        deadlines = await get_all_deadlines(session, active_only=False)
        deadline = next((d for d in deadlines if d.id == deadline_id), None)
        
        if not deadline:
            await callback.answer("Дедлайн не найден", show_alert=True)
            return
        
        date_str = format_date(deadline.date)
        time_str = deadline.deadline_time.strftime("%H:%M")
        
        await callback.message.edit_text(
            f"⚠️ <b>Подтверждение удаления</b>\n\n"
            f"Вы уверены, что хотите удалить дедлайн:\n"
            f"📅 <b>{date_str}</b> в <b>{time_str}</b>?\n\n"
            f"Это действие нельзя отменить!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_deadline_confirm_{deadline_id}")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_deadline_{deadline_id}")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("delete_deadline_confirm_"))
async def callback_delete_deadline_confirm(callback: CallbackQuery):
    if not await check_admin(callback):
        return
    
    deadline_id = int(callback.data.replace("delete_deadline_confirm_", ""))
    
    async for session in get_session():
        from services.deadline_service import delete_deadline
        success = await delete_deadline(session, deadline_id)
        
        if success:
            await callback.message.edit_text(
                "✅ Дедлайн успешно удален",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К списку дедлайнов", callback_data="admin_deadlines")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ])
            )
            await callback.answer("Дедлайн удален")
        else:
            await callback.answer("Ошибка при удалении", show_alert=True)

