from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from aiogram import Bot
from database.database import get_session
from services.order_service import get_user_orders, get_all_orders
from services.user_service import get_all_users, is_admin
from services.report_service import get_orders_summary, get_dish_statistics, get_user_statistics, get_cafe_report
from services.cafe_service import get_all_cafes
from services.notification_service import notify_user_about_order_change
from utils.export_service import export_statistics_to_excel
from models.order import OrderStatus
from config.settings import settings
from loguru import logger
from aiogram.types import BufferedInputFile

scheduler = AsyncIOScheduler()

async def send_daily_cafe_reports(bot: Bot):
    """
    Отправляет ежедневные отчеты по кафе офис-менеджерам
    Генерирует отдельный отчет для каждого кафе с группировкой заказов
    Выполняется автоматически по расписанию (настраивается в settings)
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    async for session in get_session():
        users = await get_all_users(session)
        admin_users = [u for u in users if await is_admin(session, u.telegram_id)]
        
        if not admin_users:
            return
        
        cafes = await get_all_cafes(session, active_only=True)
        cafe_report = await get_cafe_report(session, today)
        
        if not cafe_report["cafes"]:
            report_text = (
                f"📊 Отчет по заказам на {today.strftime('%d.%m.%Y')}\n\n"
                f"На сегодня заказов нет."
            )
            for admin in admin_users:
                try:
                    await bot.send_message(admin.telegram_id, report_text)
                except Exception as e:
                    logger.error(f"Ошибка при отправке отчета админу {admin.telegram_id}: {e}")
            return
        
        for cafe_data in cafe_report["cafes"]:
            if cafe_data["total_orders"] == 0:
                continue
            
            report_text = (
                f"📊 <b>Отчет по кафе</b>\n\n"
                f"☕ <b>Кафе:</b> {cafe_data['cafe_name']}\n"
                f"📅 <b>Дата:</b> {today.strftime('%d.%m.%Y')}\n\n"
                f"📦 Всего заказов: <b>{cafe_data['total_orders']}</b>\n"
                f"👥 Уникальных сотрудников: <b>{cafe_data['unique_users']}</b>\n"
                f"🍽️ Всего позиций: <b>{cafe_data['total_items']}</b>\n"
                f"💰 Общая сумма: <b>{cafe_data['total_amount']:.0f} ₽</b>\n\n"
                f"📋 <b>Детали заказов:</b>\n\n"
            )
            
            for order_detail in cafe_data["orders"]:
                report_text += (
                    f"👤 <b>{order_detail['user_name']}</b>\n"
                    f"   📱 Telegram ID: {order_detail['telegram_id']}\n"
                    f"   🍽️ {order_detail['items']}\n"
                )
                if order_detail.get('delivery_time'):
                    report_text += f"   ⏰ Время доставки: {order_detail['delivery_time']}\n"
                if order_detail.get('delivery_type'):
                    delivery_type_text = "🚚 Доставка" if order_detail['delivery_type'] == 'delivery' else "🏃 Самовывоз"
                    report_text += f"   {delivery_type_text}\n"
                report_text += f"   💰 Сумма: {order_detail['total']:.0f} ₽\n\n"
            
            for admin in admin_users:
                try:
                    await bot.send_message(admin.telegram_id, report_text, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Ошибка при отправке отчета по кафе админу {admin.telegram_id}: {e}")

async def send_daily_report(bot: Bot):
    """
    Отправляет ежедневный отчет администраторам
    Включает сводку заказов, статистику по блюдам и пользователям
    Выполняется автоматически по расписанию (настраивается в settings)
    """
    yesterday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    
    async for session in get_session():
        users = await get_all_users(session)
        admin_users = [u for u in users if await is_admin(session, u.telegram_id)]
        
        if not admin_users:
            return
        
        summary = await get_orders_summary(session, yesterday)
        dishes = await get_dish_statistics(session, yesterday)
        users_stats = await get_user_statistics(session, yesterday)
        
        report_text = (
            f"📊 Ежедневный отчет за {yesterday.strftime('%d.%m.%Y')}\n\n"
            f"Всего заказов: {summary['total_orders']}\n"
            f"Уникальных пользователей: {summary['unique_users']}\n"
            f"Общая сумма: {summary['total_amount']:.0f} ₽"
        )
        
        stats_data = {
            "summary": summary,
            "dishes": dishes,
            "users": users_stats
        }
        
        excel_file = export_statistics_to_excel(stats_data)
        file = BufferedInputFile(
            excel_file.read(),
            filename=f"daily_report_{yesterday.strftime('%Y-%m-%d')}.xlsx"
        )
        
        for admin in admin_users:
            try:
                await bot.send_message(admin.telegram_id, report_text)
                await bot.send_document(admin.telegram_id, file, caption=f"📊 Отчет за {yesterday.strftime('%d.%m.%Y')}")
            except Exception as e:
                logger.error(f"Ошибка при отправке ежедневного отчета админу {admin.telegram_id}: {e}")

async def send_weekly_report(bot: Bot):
    """
    Отправляет еженедельный отчет администраторам
    Агрегирует данные за последние 7 дней
    Выполняется автоматически по расписанию (настраивается в settings)
    """
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    async for session in get_session():
        users = await get_all_users(session)
        admin_users = [u for u in users if await is_admin(session, u.telegram_id)]
        
        if not admin_users:
            return
        
        total_orders = 0
        total_amount = 0.0
        unique_users_set = set()
        
        for day_offset in range(7):
            date = week_start + timedelta(days=day_offset)
            summary = await get_orders_summary(session, date)
            total_orders += summary['total_orders']
            total_amount += summary['total_amount']
            for order in summary['orders']:
                unique_users_set.add(order.user_id)
        
        report_text = (
            f"📊 Еженедельный отчет\n"
            f"Период: {week_start.strftime('%d.%m.%Y')} - {(week_start + timedelta(days=6)).strftime('%d.%m.%Y')}\n\n"
            f"Всего заказов: {total_orders}\n"
            f"Уникальных пользователей: {len(unique_users_set)}\n"
            f"Общая сумма: {total_amount:.0f} ₽"
        )
        
        for admin in admin_users:
            try:
                await bot.send_message(admin.telegram_id, report_text)
            except Exception as e:
                logger.error(f"Ошибка при отправке еженедельного отчета админу {admin.telegram_id}: {e}")

async def check_deadline_reminders(bot: Bot):
    """
    Проверяет и отправляет напоминания о дедлайне заказа
    Отправляет напоминания за 1 час и за 30 минут до дедлайна
    Выполняется каждую минуту для проверки текущего времени
    """
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    deadline_time = today.replace(
        hour=settings.ORDER_DEADLINE_HOUR,
        minute=settings.ORDER_DEADLINE_MINUTE,
        second=0,
        microsecond=0
    )
    
    reminder_1h = deadline_time - timedelta(hours=1)
    reminder_30m = deadline_time - timedelta(minutes=30)
    
    should_send_1h = (now.hour == reminder_1h.hour and now.minute == reminder_1h.minute)
    should_send_30m = (now.hour == reminder_30m.hour and now.minute == reminder_30m.minute)
    
    if not (should_send_1h or should_send_30m):
        return
    
    async for session in get_session():
        all_orders = await get_all_orders(session, today)
        today_orders = [o for o in all_orders if o.status == OrderStatus.PENDING and o.order_date.date() == today.date()]
        
        for order in today_orders:
            try:
                if should_send_1h:
                    message = (
                        f"⏰ Напоминание!\n\n"
                        f"До дедлайна заказа остался 1 час.\n"
                        f"Ваш заказ на {order.order_date.strftime('%d.%m.%Y')} будет принят до {settings.ORDER_DEADLINE_HOUR:02d}:{settings.ORDER_DEADLINE_MINUTE:02d}.\n\n"
                        f"Для просмотра заказа используйте /orders"
                    )
                    await notify_user_about_order_change(bot, order.user.telegram_id, message)
                
                elif should_send_30m:
                    message = (
                        f"⏰ Напоминание!\n\n"
                        f"До дедлайна заказа осталось 30 минут!\n"
                        f"Ваш заказ на {order.order_date.strftime('%d.%m.%Y')} будет принят до {settings.ORDER_DEADLINE_HOUR:02d}:{settings.ORDER_DEADLINE_MINUTE:02d}.\n\n"
                        f"Для просмотра заказа используйте /orders"
                    )
                    await notify_user_about_order_change(bot, order.user.telegram_id, message)
            except Exception as e:
                logger.error(f"Ошибка при отправке напоминания для заказа {order.id}: {e}")

def setup_scheduler(bot: Bot):
    scheduler.add_job(
        check_deadline_reminders,
        trigger=CronTrigger(minute="*"),
        args=[bot],
        id="deadline_reminders",
        replace_existing=True
    )
    
    scheduler.add_job(
        send_daily_cafe_reports,
        CronTrigger(hour=settings.DAILY_REPORT_HOUR, minute=settings.DAILY_REPORT_MINUTE),
        args=[bot],
        id="daily_cafe_reports",
        replace_existing=True
    )
    
    scheduler.add_job(
        send_daily_report,
        CronTrigger(hour=settings.DAILY_REPORT_HOUR, minute=settings.DAILY_REPORT_MINUTE),
        args=[bot],
        id="daily_report",
        replace_existing=True
    )
    
    scheduler.add_job(
        send_weekly_report,
        CronTrigger(day_of_week=settings.WEEKLY_REPORT_DAY, hour=settings.WEEKLY_REPORT_HOUR, minute=settings.WEEKLY_REPORT_MINUTE),
        args=[bot],
        id="weekly_report",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Планировщик задач запущен")
