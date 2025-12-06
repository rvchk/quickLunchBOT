"""
Скрипт для настройки тестового окружения
"""
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import asyncio
from database.database import init_db, get_session
from models.dish import Dish
from models.menu import Menu
from sqlalchemy import select
from datetime import datetime, timedelta

async def setup_test_environment():
    """Настройка тестового окружения"""
    print("Инициализация базы данных...")
    await init_db()
    
    async for session in get_session():
        result = await session.execute(select(Dish))
        existing_dishes = result.scalars().all()
        
        if existing_dishes:
            print(f"База данных уже содержит {len(existing_dishes)} блюд")
            return
        
        print("Создание тестовых данных...")
        dishes_data = [
            {"name": "Борщ", "description": "Классический борщ со сметаной", "price": 250.0, "category": "Первые блюда"},
            {"name": "Солянка", "description": "Мясная солянка", "price": 280.0, "category": "Первые блюда"},
            {"name": "Куриный суп", "description": "Куриный суп с лапшой", "price": 200.0, "category": "Первые блюда"},
            {"name": "Греческий салат", "description": "Свежие овощи с оливковым маслом", "price": 180.0, "category": "Салаты"},
            {"name": "Цезарь", "description": "Салат Цезарь с курицей", "price": 220.0, "category": "Салаты"},
            {"name": "Оливье", "description": "Классический салат Оливье", "price": 150.0, "category": "Салаты"},
            {"name": "Котлета по-киевски", "description": "Куриная котлета с маслом", "price": 320.0, "category": "Горячее"},
            {"name": "Плов", "description": "Узбекский плов с бараниной", "price": 350.0, "category": "Горячее"},
            {"name": "Паста карбонара", "description": "Паста с беконом и сливками", "price": 290.0, "category": "Горячее"},
            {"name": "Пицца Маргарита", "description": "Классическая пицца", "price": 400.0, "category": "Горячее"},
        ]
        
        dishes = []
        for dish_data in dishes_data:
            dish = Dish(**dish_data)
            session.add(dish)
            dishes.append(dish)
        
        await session.commit()
        
        for dish in dishes:
            await session.refresh(dish)
        
        tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        for dish in dishes:
            menu_item = Menu(
                date=tomorrow,
                dish_id=dish.id,
                available_quantity=50
            )
            session.add(menu_item)
        
        await session.commit()
        print(f"Создано {len(dishes)} блюд и меню на завтра")
        print("\nТестовое окружение готово!")

if __name__ == "__main__":
    asyncio.run(setup_test_environment())

