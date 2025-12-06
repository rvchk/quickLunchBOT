@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   Запуск Telegram бота
echo ========================================
echo.

REM Проверка наличия Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ОШИБКА] Python не найден в PATH!
    echo Установите Python с https://www.python.org/
    pause
    exit /b 1
)

echo [OK] Python найден
python --version
echo.

REM Переход в директорию скрипта
cd /d "%~dp0"

REM Проверка и создание виртуального окружения
if not exist "venv\" (
    echo [INFO] Создание виртуального окружения...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ОШИБКА] Не удалось создать виртуальное окружение!
        pause
        exit /b 1
    )
    echo [OK] Виртуальное окружение создано
) else (
    echo [OK] Виртуальное окружение найдено
)
echo.

REM Активация виртуального окружения
echo [INFO] Активация виртуального окружения...
call venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo [ОШИБКА] Не удалось активировать виртуальное окружение!
    pause
    exit /b 1
)
echo [OK] Виртуальное окружение активировано
echo.

REM Обновление pip
echo [INFO] Обновление pip...
python -m pip install --upgrade pip --quiet
echo [OK] pip обновлен
echo.

REM Создание тестовых данных (если нужно)
if not exist "lunch_bot.db" (
    echo [INFO] База данных не найдена, создание тестовых данных...
    python scripts\init_db.py
    echo.
)

REM Установка зависимостей
if exist "requirements.txt" (
    echo [INFO] Установка зависимостей из requirements.txt...
    pip install -r requirements.txt --quiet
    if %ERRORLEVEL% NEQ 0 (
        echo [ОШИБКА] Не удалось установить зависимости!
        pause
        exit /b 1
    )
    echo [OK] Зависимости установлены
) else (
    echo [ПРЕДУПРЕЖДЕНИЕ] Файл requirements.txt не найден!
)
echo.

REM Проверка наличия .env файла
if not exist ".env" (
    echo [ВНИМАНИЕ] Файл .env не найден!
    if exist "env.example" (
        echo [INFO] Найден файл env.example
        echo.
        echo Вы хотите создать .env файл из env.example? (Y/N)
        set /p CREATE_ENV=
        if /i "!CREATE_ENV!"=="Y" (
            copy env.example .env >nul
            echo [OK] Файл .env создан из env.example
            echo [ВАЖНО] Отредактируйте файл .env и укажите BOT_TOKEN и другие настройки!
            echo.
            pause
        ) else (
            echo [ОШИБКА] Для работы бота необходим файл .env с настройками!
            pause
            exit /b 1
        )
    ) else (
        echo [ОШИБКА] Файл .env не найден и env.example тоже отсутствует!
        echo Создайте файл .env с необходимыми настройками.
        pause
        exit /b 1
    )
) else (
    echo [OK] Файл .env найден
)
echo.

REM Создание папки для логов, если её нет
if not exist "logs\" (
    mkdir logs
    echo [OK] Папка logs создана
)

echo ========================================
echo   Запуск бота...
echo ========================================
echo.

REM Запуск приложения
python run.py

REM Если скрипт завершился, показываем сообщение
echo.
echo ========================================
echo   Бот остановлен
echo ========================================
pause




