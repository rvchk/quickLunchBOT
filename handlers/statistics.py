from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.database import get_session
from services.user_service import get_or_create_user
from services.report_service import get_user_personal_statistics, get_popular_dishes
from utils.formatters import format_date

router = Router()

@router.callback_query(lambda c: c.data == "my_statistics")
async def callback_my_statistics(callback: CallbackQuery):
    async for session in get_session():
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.full_name
        )
        
        stats = await get_user_personal_statistics(session, user.id)
        
        period_text = ""
        if stats["date_from"] or stats["date_to"]:
            period_text = "\n📅 <b>Период:</b> "
            if stats["date_from"]:
                period_text += f"с {format_date(stats['date_from'])} "
            if stats["date_to"]:
                period_text += f"по {format_date(stats['date_to'])}"
        else:
            period_text = "\n📅 <b>Период:</b> Все время"
        
        stats_text = f"""💰 <b>Моя статистика</b>{period_text}

📦 <b>Всего заказов:</b> {stats['orders_count']}
💵 <b>Потрачено всего:</b> {stats['total_amount']:.0f} ₽
🍽️ <b>Всего блюд заказано:</b> {stats['total_items']}
📊 <b>Средний чек:</b> {stats['avg_order']:.0f} ₽"""

        if stats['top_dishes']:
            stats_text += "\n\n⭐ <b>Ваши любимые блюда:</b>\n"
            for i, dish in enumerate(stats['top_dishes'], 1):
                stats_text += f"{i}. {dish['name']} - {dish['count']} раз ({dish['total_amount']:.0f} ₽)\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 За период", callback_data="statistics_period")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()

@router.callback_query(lambda c: c.data == "recommendations")
async def callback_recommendations(callback: CallbackQuery):
    async for session in get_session():
        popular_dishes = await get_popular_dishes(session, limit=5)
        
        if not popular_dishes:
            await callback.message.edit_text(
                "⭐ <b>Рекомендации</b>\n\n"
                "Пока нет данных для рекомендаций. Попробуйте создать заказ!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        recommendations_text = "⭐ <b>Популярные блюда</b>\n\n"
        recommendations_text += "💡 Эти блюда пользуются наибольшей популярностью:\n\n"
        
        for i, dish in enumerate(popular_dishes, 1):
            recommendations_text += f"{i}. <b>{dish['name']}</b>\n"
            recommendations_text += f"   📊 Заказано: {dish['quantity']} раз\n"
            recommendations_text += f"   💰 Выручка: {dish['revenue']:.0f} ₽\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Создать заказ", callback_data="create_order")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")]
        ])
        
        await callback.message.edit_text(
            recommendations_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()

