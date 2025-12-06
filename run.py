"""
Скрипт для запуска проекта с правильной настройкой путей
"""
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    from main import main
    import asyncio
    asyncio.run(main())









