from aiogram import Router
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

router = Router()

@router.callback_query(lambda c: c.data == "help")
async def callback_help(callback: CallbackQuery):
    from config.settings import settings
    from utils.keyboards import get_back_keyboard
    help_text = f"""
📖 <b>Помощь</b>

🎯 <b>Основные функции:</b>

🍽️ <b>Создать заказ</b>
   Выберите дату и блюда для заказа

📦 <b>Мои заказы</b>
   Просмотрите ваши текущие заказы

📊 <b>История</b>
   Посмотрите историю всех ваших заказов

⏰ <b>Дедлайн заказа:</b>

До <b>{settings.ORDER_DEADLINE_HOUR:02d}:{settings.ORDER_DEADLINE_MINUTE:02d}</b> дня заказа

⌨️ <b>Команды:</b>

/start - Главное меню
/menu - Просмотр меню
/orders - Мои заказы
/help - Эта справка
/cancel - Отменить текущую операцию

💡 <b>Совет:</b> Используйте кнопки для навигации по боту
    """
    await callback.message.edit_text(help_text, reply_markup=get_back_keyboard())
    await callback.answer()

@router.callback_query(lambda c: c.data == "cancel")
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    from utils.keyboards import get_main_menu_keyboard
    from database.database import get_session
    from services.user_service import get_or_create_user, is_admin
    
    async for session in get_session():
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.full_name
        )
        user_is_admin = await is_admin(session, user.telegram_id)
        
        await callback.message.edit_text(
            "❌ <b>Операция отменена</b>\n\n"
            "💡 Выберите действие из главного меню:",
            reply_markup=get_main_menu_keyboard(is_admin=user_is_admin),
            parse_mode="HTML"
        )
        await callback.answer()
        return

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    await state.clear()
    
    from utils.keyboards import get_main_menu_keyboard, get_back_keyboard
    from database.database import get_session
    from services.user_service import get_or_create_user, is_admin
    
    async for session in get_session():
        user = await get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name
        )
        user_is_admin = await is_admin(session, user.telegram_id)
        
        if current_state:
            state_name = str(current_state)
            if "DishManagementStates" in state_name or "LoadMenuStates" in state_name:
                await message.answer(
                    "❌ <b>Операция отменена</b>\n\n"
                    "💡 Вы можете вернуться к управлению меню.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="◀️ К управлению меню", callback_data="admin_menu")],
                        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                    ]),
                    parse_mode="HTML"
                )
            elif "OrderStates" in state_name:
                await message.answer(
                    "❌ <b>Создание заказа отменено</b>\n\n"
                    "💡 Вы можете начать новый заказ из главного меню.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📋 Создать заказ", callback_data="create_order")],
                        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                    ]),
                    parse_mode="HTML"
                )
            elif "HistoryFilterStates" in state_name or "AdminOrderFilterStates" in state_name:
                await message.answer(
                    "❌ <b>Фильтрация отменена</b>\n\n"
                    "💡 Выберите действие из главного меню:",
                    reply_markup=get_main_menu_keyboard(is_admin=user_is_admin),
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    "❌ <b>Операция отменена</b>\n\n"
                    "💡 Выберите действие из главного меню:",
                    reply_markup=get_main_menu_keyboard(is_admin=user_is_admin),
                    parse_mode="HTML"
                )
        else:
            await message.answer(
                "❌ <b>Нет активных операций для отмены</b>\n\n"
                "💡 Выберите действие из главного меню:",
                reply_markup=get_main_menu_keyboard(is_admin=user_is_admin),
                parse_mode="HTML"
            )
        return

@router.callback_query(lambda c: c.data == "start")
async def callback_start(callback: CallbackQuery, state: FSMContext):
    # Проверяем незавершенную корзину ПЕРЕД очисткой state
    data = await state.get_data()
    cart = data.get("cart", [])
    saved_order_date = data.get("order_date")
    
    # Очищаем только текущее состояние, но сохраняем корзину
    current_state = await state.get_state()
    if current_state:
        await state.set_state(None)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from database.database import get_session
    from services.user_service import get_or_create_user, is_admin
    from utils.keyboards import get_main_menu_keyboard
    from utils.formatters import format_date
    
    async for session in get_session():
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.full_name
        )
        
        from utils.keyboards import get_main_menu_keyboard
        user_is_admin = await is_admin(session, user.telegram_id)
        
        # Получаем главное меню
        keyboard = get_main_menu_keyboard(is_admin=user_is_admin)
        
        # Если есть незавершенная корзина, добавляем кнопку в начало
        if cart and saved_order_date:
            total = sum(item["price"] * item["quantity"] for item in cart)
            keyboard.inline_keyboard.insert(0, [
                InlineKeyboardButton(
                    text=f"🛒 Вернуться к корзине ({len(cart)} шт., {total:.0f} ₽)",
                    callback_data="return_to_cart"
                )
            ])
        
        welcome_text = f"""
👋 <b>Добро пожаловать!</b>

Привет, <b>{callback.from_user.first_name}</b>! 👨‍🍳

Я помогу вам организовать заказы на обед быстро и удобно.

📋 <b>Что я умею:</b>

✨ Создавать и управлять заказами
📊 Просматривать историю заказов
🛒 Управлять корзиной
📅 Выбирать блюда на любую дату

💡 Выберите действие из меню ниже 👇"""
        
        if cart and saved_order_date:
            welcome_text += f"\n\n🛒 У вас есть незавершенная корзина на {format_date(saved_order_date)}"
        
        await callback.message.edit_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()

