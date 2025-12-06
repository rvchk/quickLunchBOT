import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from database.database import init_db, get_session
from models.user import User, UserRole
from models.dish import Dish
from models.cafe_menu import CafeMenu
from models.office import Office
from models.cafe import Cafe
from models.order import Order, OrderItem, OrderStatus
from models.order_deadline import OrderDeadline
from sqlalchemy import select, delete

async def create_test_data(force: bool = False):
    """
    Создает тестовые данные для бота:
    - Блюда в различных категориях
    - Меню на неделю вперед
    - Тестовые заказы (опционально)
    
    Args:
        force: Если True, удаляет существующие данные и создает заново
    """
    print("[INFO] Инициализация базы данных...")
    await init_db()
    
    async for session in get_session():
        # Проверяем существующие данные
        result = await session.execute(select(Dish))
        existing_dishes = result.scalars().all()
        
        if existing_dishes and not force:
            print("[WARNING] Тестовые данные уже существуют")
            print("[TIP] Используйте --force для пересоздания данных")
            return
        
        if force and existing_dishes:
            print("[INFO] Удаление существующих данных...")
            await session.execute(delete(CafeMenu))
            await session.execute(delete(OrderDeadline))
            await session.execute(delete(Order))
            await session.execute(delete(Cafe))
            await session.execute(delete(Office))
            await session.execute(delete(Dish))
            await session.commit()
            print("[OK] Старые данные удалены")
        
        print("[INFO] Создание блюд...")
        
        dishes_data = [
            # Первые блюда
            {"name": "Борщ", "description": "Классический борщ со сметаной и зеленью", "price": 250.0, "category": "Первые блюда"},
            {"name": "Солянка", "description": "Мясная солянка с оливками и лимоном", "price": 280.0, "category": "Первые блюда"},
            {"name": "Куриный суп", "description": "Куриный суп с лапшой и овощами", "price": 200.0, "category": "Первые блюда"},
            {"name": "Грибной крем-суп", "description": "Нежный крем-суп из шампиньонов", "price": 220.0, "category": "Первые блюда"},
            {"name": "Уха", "description": "Наваристая уха из свежей рыбы", "price": 300.0, "category": "Первые блюда"},
            
            # Салаты
            {"name": "Греческий салат", "description": "Свежие овощи, фета, оливки с оливковым маслом", "price": 180.0, "category": "Салаты"},
            {"name": "Цезарь", "description": "Салат Цезарь с курицей и сухариками", "price": 220.0, "category": "Салаты"},
            {"name": "Оливье", "description": "Классический салат Оливье с колбасой", "price": 150.0, "category": "Салаты"},
            {"name": "Винегрет", "description": "Овощной винегрет с растительным маслом", "price": 130.0, "category": "Салаты"},
            {"name": "Салат с тунцом", "description": "Салат из свежих овощей с тунцом", "price": 240.0, "category": "Салаты"},
            {"name": "Капрезе", "description": "Помидоры, моцарелла, базилик, бальзамик", "price": 260.0, "category": "Салаты"},
            
            # Горячее
            {"name": "Котлета по-киевски", "description": "Куриная котлета с маслом и зеленью", "price": 320.0, "category": "Горячее"},
            {"name": "Плов", "description": "Узбекский плов с бараниной и специями", "price": 350.0, "category": "Горячее"},
            {"name": "Паста карбонара", "description": "Паста с беконом, сливками и пармезаном", "price": 290.0, "category": "Горячее"},
            {"name": "Пицца Маргарита", "description": "Классическая пицца с томатами и моцареллой", "price": 400.0, "category": "Горячее"},
            {"name": "Бифштекс", "description": "Говяжий бифштекс с овощами", "price": 450.0, "category": "Горячее"},
            {"name": "Рыба на пару", "description": "Филе лосося на пару с овощами", "price": 380.0, "category": "Горячее"},
            {"name": "Куриные крылышки", "description": "Запеченные куриные крылышки в соусе", "price": 280.0, "category": "Горячее"},
            {"name": "Роллы Калифорния", "description": "Роллы с крабом, авокадо и огурцом (6 шт)", "price": 320.0, "category": "Горячее"},
            
            # Гарниры
            {"name": "Картофель фри", "description": "Хрустящий картофель фри", "price": 120.0, "category": "Гарниры"},
            {"name": "Рис с овощами", "description": "Отварной рис с овощами", "price": 100.0, "category": "Гарниры"},
            {"name": "Гречка", "description": "Отварная гречка с маслом", "price": 90.0, "category": "Гарниры"},
            {"name": "Овощи на гриле", "description": "Смесь овощей на гриле", "price": 140.0, "category": "Гарниры"},
            
            # Напитки
            {"name": "Кофе эспрессо", "description": "Классический эспрессо", "price": 80.0, "category": "Напитки"},
            {"name": "Капучино", "description": "Капучино с молочной пенкой", "price": 120.0, "category": "Напитки"},
            {"name": "Чай черный", "description": "Черный чай на выбор", "price": 60.0, "category": "Напитки"},
            {"name": "Сок апельсиновый", "description": "Свежевыжатый апельсиновый сок", "price": 100.0, "category": "Напитки"},
            {"name": "Морс клюквенный", "description": "Домашний клюквенный морс", "price": 90.0, "category": "Напитки"},
            
            # Десерты
            {"name": "Чизкейк", "description": "Классический чизкейк с ягодным соусом", "price": 180.0, "category": "Десерты"},
            {"name": "Тирамису", "description": "Итальянский десерт тирамису", "price": 200.0, "category": "Десерты"},
            {"name": "Мороженое", "description": "Мороженое на выбор (пломбир, ванильное, шоколадное)", "price": 100.0, "category": "Десерты"},
            {"name": "Блины с вареньем", "description": "Тонкие блины с домашним вареньем", "price": 150.0, "category": "Десерты"},
        ]
        
        dishes = []
        for dish_data in dishes_data:
            dish = Dish(**dish_data, available=True)
            session.add(dish)
            dishes.append(dish)
        
        await session.commit()
        
        # Обновляем ID блюд
        for dish in dishes:
            await session.refresh(dish)
        
        print(f"[OK] Создано {len(dishes)} блюд")
        
        print("[INFO] Создание офисов...")
        offices_data = [
            {"name": "Главный офис", "address": "Москва, ул. Тверская, д. 1"},
            {"name": "Офис на Ленинском", "address": "Москва, Ленинский проспект, д. 50"},
            {"name": "Офис на Садовом", "address": "Москва, Садовое кольцо, д. 25"},
        ]
        
        offices = []
        for office_data in offices_data:
            office = Office(**office_data, is_active=True)
            session.add(office)
            offices.append(office)
        
        await session.commit()
        for office in offices:
            await session.refresh(office)
        print(f"[OK] Создано {len(offices)} офисов")
        
        print("[INFO] Создание кафе...")
        cafes_data = [
            {"name": "Кафе 'Уютное'", "office_id": offices[0].id, "contact_info": "+7 (495) 123-45-67"},
            {"name": "Столовая 'Вкусно'", "office_id": offices[0].id, "contact_info": "+7 (495) 234-56-78"},
            {"name": "Кафе 'Быстрое'", "office_id": offices[1].id, "contact_info": "+7 (495) 345-67-89"},
            {"name": "Ресторан 'Элит'", "office_id": offices[2].id, "contact_info": "+7 (495) 456-78-90"},
        ]
        
        cafes = []
        for cafe_data in cafes_data:
            cafe = Cafe(**cafe_data, is_active=True)
            session.add(cafe)
            cafes.append(cafe)
        
        await session.commit()
        for cafe in cafes:
            await session.refresh(cafe)
        print(f"[OK] Создано {len(cafes)} кафе")
        
        print("[INFO] Создание меню для кафе на неделю...")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        menu_items_created = 0
        
        for day_offset in range(7):
            menu_date = today + timedelta(days=day_offset)
            base_quantity = 50 if day_offset == 0 else (40 if day_offset < 3 else 60)
            
            for cafe in cafes:
                for dish in dishes:
                    if dish.category in ["Десерты", "Напитки"] and day_offset % 2 == 0:
                        continue
                    
                    menu_item = CafeMenu(
                        cafe_id=cafe.id,
                        dish_id=dish.id,
                        date=menu_date,
                        available_quantity=base_quantity
                    )
                    session.add(menu_item)
                    menu_items_created += 1
        
        await session.commit()
        print(f"[OK] Создано меню для {len(cafes)} кафе на 7 дней ({menu_items_created} позиций)")
        
        print("[INFO] Создание дедлайнов...")
        deadline_time = today.replace(hour=12, minute=0, second=0, microsecond=0)
        
        for day_offset in range(7):
            deadline_date = today + timedelta(days=day_offset)
            deadline_datetime = deadline_date.replace(hour=12, minute=0)
            
            for office in offices:
                deadline = OrderDeadline(
                    date=deadline_date,
                    deadline_time=deadline_datetime,
                    office_id=office.id,
                    is_active=True
                )
                session.add(deadline)
        
        await session.commit()
        print(f"[OK] Создано дедлайнов для офисов")
        
        # Опционально: создаем тестовые заказы на сегодня и завтра
        print("[INFO] Создание тестовых заказов...")
        
        print("[INFO] Создание тестового пользователя...")
        test_user = User(
            telegram_id=999999999,
            username="test_user",
            full_name="Тестовый Пользователь",
            role=UserRole.USER,
            office_id=offices[0].id
        )
        session.add(test_user)
        await session.commit()
        await session.refresh(test_user)
        print(f"[OK] Создан тестовый пользователь (офис: {offices[0].name})")
        
        print("[INFO] Создание тестовых заказов...")
        today_orders = [
            {
                "date": today,
                "cafe_id": cafes[0].id,
                "items": [
                    {"dish_id": dishes[0].id, "quantity": 1, "price": dishes[0].price},
                    {"dish_id": dishes[11].id, "quantity": 1, "price": dishes[11].price},
                    {"dish_id": dishes[20].id, "quantity": 1, "price": dishes[20].price},
                ]
            },
            {
                "date": today,
                "cafe_id": cafes[1].id,
                "items": [
                    {"dish_id": dishes[5].id, "quantity": 1, "price": dishes[5].price},
                    {"dish_id": dishes[13].id, "quantity": 2, "price": dishes[13].price},
                ]
            },
        ]
        
        tomorrow = today + timedelta(days=1)
        tomorrow_orders = [
            {
                "date": tomorrow,
                "cafe_id": cafes[0].id,
                "items": [
                    {"dish_id": dishes[1].id, "quantity": 1, "price": dishes[1].price},
                    {"dish_id": dishes[14].id, "quantity": 1, "price": dishes[14].price},
                    {"dish_id": dishes[25].id, "quantity": 1, "price": dishes[25].price},
                ]
            },
        ]
        
        orders_created = 0
        for order_data in today_orders + tomorrow_orders:
            order = Order(
                user_id=test_user.id,
                cafe_id=order_data.get("cafe_id"),
                order_date=order_data["date"],
                status=OrderStatus.PENDING,
                total_amount=sum(item["price"] * item["quantity"] for item in order_data["items"])
            )
            session.add(order)
            await session.flush()
            
            for item_data in order_data["items"]:
                order_item = OrderItem(
                    order_id=order.id,
                    dish_id=item_data["dish_id"],
                    quantity=item_data["quantity"],
                    price=item_data["price"]
                )
                session.add(order_item)
            
            orders_created += 1
        
        await session.commit()
        print(f"[OK] Создано {orders_created} тестовых заказов")
        
        print("\n" + "="*50)
        print("[SUCCESS] Тестовые данные успешно созданы!")
        print("="*50)
        print(f"[STATS] Статистика:")
        print(f"   - Офисов: {len(offices)}")
        print(f"   - Кафе: {len(cafes)}")
        print(f"   - Блюд: {len(dishes)}")
        print(f"   - Позиций в меню: {menu_items_created}")
        print(f"   - Дедлайнов: {len(offices) * 7}")
        print(f"   - Тестовых заказов: {orders_created}")
        print(f"   - Категорий: {len(set(d.category for d in dishes))}")
        print("\n[TIP] Теперь вы можете запустить бота и протестировать функциональность!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Создание тестовых данных для бота")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Удалить существующие данные и создать заново"
    )
    
    args = parser.parse_args()
    asyncio.run(create_test_data(force=args.force))













