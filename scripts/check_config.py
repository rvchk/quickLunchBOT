"""
Скрипт для проверки конфигурации проекта
Проверяет наличие всех необходимых переменных окружения и их корректность
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def check_env_file():
    """Проверяет наличие .env файла"""
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ Файл .env не найден!")
        print("   Создайте его на основе env.example:")
        print("   cp env.example .env")
        return False
    print("✅ Файл .env найден")
    return True

def check_bot_token():
    """Проверяет наличие BOT_TOKEN"""
    token = os.getenv("BOT_TOKEN", "")
    if not token or token == "your_bot_token_here":
        print("❌ BOT_TOKEN не установлен или имеет значение по умолчанию")
        print("   Установите токен бота в .env файле")
        return False
    if len(token) < 40:
        print("⚠️  BOT_TOKEN выглядит некорректно (слишком короткий)")
        return False
    print("✅ BOT_TOKEN установлен")
    return True

def check_database_url():
    """Проверяет DATABASE_URL"""
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("⚠️  DATABASE_URL не установлен, будет использовано значение по умолчанию (SQLite)")
        return True
    
    if db_url.startswith("sqlite"):
        print("✅ DATABASE_URL: SQLite (для разработки)")
    elif db_url.startswith("postgresql"):
        print("✅ DATABASE_URL: PostgreSQL (для продакшена)")
    else:
        print("⚠️  DATABASE_URL имеет нестандартный формат")
    
    return True

def check_admin_ids():
    """Проверяет ADMIN_IDS"""
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    if not admin_ids_str:
        print("⚠️  ADMIN_IDS не установлен")
        print("   Бот будет работать, но админ-панель будет недоступна")
        return True
    
    try:
        admin_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]
        if not admin_ids:
            print("⚠️  ADMIN_IDS пуст")
            return True
        print(f"✅ ADMIN_IDS установлен: {len(admin_ids)} администратор(ов)")
        return True
    except ValueError:
        print("❌ ADMIN_IDS содержит некорректные значения")
        print("   Формат: ADMIN_IDS=123456789,987654321")
        return False

def check_deadline_settings():
    """Проверяет настройки дедлайна заказа"""
    hour = os.getenv("ORDER_DEADLINE_HOUR", "12")
    minute = os.getenv("ORDER_DEADLINE_MINUTE", "0")
    
    try:
        hour_int = int(hour)
        minute_int = int(minute)
        if 0 <= hour_int <= 23 and 0 <= minute_int <= 59:
            print(f"✅ ORDER_DEADLINE: {hour_int:02d}:{minute_int:02d}")
            return True
        else:
            print("❌ ORDER_DEADLINE имеет некорректные значения")
            return False
    except ValueError:
        print("❌ ORDER_DEADLINE содержит некорректные значения")
        return False

def check_report_settings():
    """Проверяет настройки отчетов"""
    daily_hour = os.getenv("DAILY_REPORT_HOUR", "18")
    daily_minute = os.getenv("DAILY_REPORT_MINUTE", "0")
    weekly_day = os.getenv("WEEKLY_REPORT_DAY", "0")
    weekly_hour = os.getenv("WEEKLY_REPORT_HOUR", "18")
    weekly_minute = os.getenv("WEEKLY_REPORT_MINUTE", "0")
    
    try:
        int(daily_hour)
        int(daily_minute)
        int(weekly_day)
        int(weekly_hour)
        int(weekly_minute)
        print("✅ Настройки отчетов установлены")
        return True
    except ValueError:
        print("❌ Настройки отчетов содержат некорректные значения")
        return False

def check_directories():
    """Проверяет наличие необходимых директорий"""
    directories = ["logs", "backups"]
    all_exist = True
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"✅ Создана директория: {dir_name}")
        else:
            print(f"✅ Директория {dir_name} существует")
    
    return True

def main():
    """Главная функция проверки"""
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("Проверка конфигурации проекта...\n")
    
    load_dotenv()
    
    checks = [
        ("Файл .env", check_env_file),
        ("BOT_TOKEN", check_bot_token),
        ("DATABASE_URL", check_database_url),
        ("ADMIN_IDS", check_admin_ids),
        ("ORDER_DEADLINE", check_deadline_settings),
        ("Настройки отчетов", check_report_settings),
        ("Директории", check_directories),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Ошибка при проверке {name}: {e}")
            results.append((name, False))
        print()
    
    print("=" * 50)
    print("📊 Результаты проверки:")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print("=" * 50)
    print(f"Пройдено: {passed}/{total}")
    
    if passed == total:
        print("\n✅ Все проверки пройдены! Проект готов к запуску.")
        return 0
    else:
        print("\n⚠️  Некоторые проверки не пройдены. Исправьте ошибки перед запуском.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

