"""
Утилиты для создания клавиатур с кнопками навигации
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Optional


def get_back_keyboard(back_callback: str = "start", text: str = "🏠 Главное меню") -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с одной кнопкой возврата
    
    Args:
        back_callback: callback_data для кнопки возврата
        text: текст кнопки возврата
    
    Returns:
        InlineKeyboardMarkup с кнопкой возврата
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=back_callback)]
    ])


def add_back_button(
    keyboard_buttons: List[List[InlineKeyboardButton]], 
    back_callback: str = "start",
    text: str = "🏠 Главное меню"
) -> List[List[InlineKeyboardButton]]:
    """
    Добавляет кнопку возврата в существующий список кнопок
    
    Args:
        keyboard_buttons: список списков кнопок
        back_callback: callback_data для кнопки возврата
        text: текст кнопки возврата
    
    Returns:
        Обновленный список кнопок с кнопкой возврата
    """
    result = keyboard_buttons.copy()
    result.append([InlineKeyboardButton(text=text, callback_data=back_callback)])
    return result


def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """
    Создает главное меню с кнопками
    
    Args:
        is_admin: является ли пользователь администратором
    
    Returns:
        InlineKeyboardMarkup главного меню
    """
    keyboard_buttons = [
        [InlineKeyboardButton(text="📋 Создать заказ", callback_data="create_order")],
        [InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton(text="📊 История", callback_data="order_history")],
        [InlineKeyboardButton(text="💰 Моя статистика", callback_data="my_statistics")],
        [InlineKeyboardButton(text="⭐ Рекомендации", callback_data="recommendations")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ]
    
    if is_admin:
        keyboard_buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_cancel_keyboard(cancel_callback: str = "cancel") -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой отмены и возврата
    
    Args:
        cancel_callback: callback_data для кнопки отмены
    
    Returns:
        InlineKeyboardMarkup с кнопками отмены и возврата
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_callback)],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
    ])

