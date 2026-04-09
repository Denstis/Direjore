@echo off
chcp 65001 >nul
REM Conductor App - Windows Launcher
REM Запуск приложения "Дирижёр" на Windows

echo ============================================
echo    🎭 Conductor - Multi-Agent Development System
echo ============================================
echo.

REM Проверка наличия Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Ошибка: Python не найден!
    echo.
    echo Установите Python 3.10+ с https://python.org
    echo ⚠️ При установке отметьте галочку "Add Python to PATH"
    pause
    exit /b 1
)

echo ✅ Python найден:
python --version
echo.

REM Переход в директорию скрипта
cd /d "%~dp0"

REM Переход в папку conductor_app
cd /d "%~dp0conductor_app"

REM Создание виртуального окружения если отсутствует
if not exist "venv\Scripts\activate.bat" (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Ошибка при создании venv!
        pause
        exit /b 1
    )
    echo ✅ Виртуальное окружение создано.
) else (
    echo ✅ Виртуальное окружение найдено.
)

echo.
echo 🔧 Активация виртуального окружения...
call venv\Scripts\activate.bat

echo.
echo 📦 Установка зависимостей...
pip install -q -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️ Предупреждение: некоторые зависимости не удалось установить.
) else (
    echo ✅ Зависимости установлены.
)

echo.
echo ============================================
echo   🚀 Запуск приложения...
echo ============================================
echo.
echo 💡 Убедитесь, что LM Studio запущен с моделью на localhost:1234
echo 💡 Для остановки нажмите Ctrl+C
echo.

REM Запуск приложения
python -m gui.app

REM Если приложение завершилось с ошибкой
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================
    echo   ❌ Приложение завершено с кодом ошибки %ERRORLEVEL%
    echo   Проверьте логи в projects/*/logs/
    echo ============================================
    pause
) else (
    echo.
    echo ============================================
    echo   ✅ Приложение завершено.
    echo ============================================
    pause
)
