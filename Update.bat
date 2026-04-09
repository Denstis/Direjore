@echo off
chcp 65001 >nul
REM Conductor App - Git Update Script
REM Обновление проекта из Git репозитория

setlocal enabledelayedexpansion

echo ============================================
echo   🔄 Conductor - Обновление из Git
echo ============================================
echo.

REM Проверка наличия Git
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Ошибка: Git не найден в PATH!
    echo.
    echo Установите Git с https://git-scm.com/download/win
    echo Или добавьте Git в переменную окружения PATH.
    pause
    exit /b 1
)

echo ✅ Git найден:
git --version
echo.

REM Переход в директорию скрипта
cd /d "%~dp0"

REM Проверка наличия репозитория .git в текущей директории
if not exist ".git" (
    echo ❌ Ошибка: Папка .git не найдена!
    echo.
    echo Это не Git-репозиторий.
    echo Запускайте Update.bat из корневой папки проекта, где находится .git
    echo Если это новая установка, используйте Run.bat вместо Update.bat.
    pause
    exit /b 1
)

echo 📂 Текущая ветка:
git branch --show-current
echo.

echo 🔍 Проверка статуса репозитория...
git status --short
echo.

REM Сохранение локальных изменений (если есть)
git diff --quiet
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️ Обнаружены локальные изменения!
    echo.
    echo Выберите действие:
    echo   1 - Сохранить изменения в stash и обновиться (рекомендуется)
    echo   2 - Отменить изменения и обновиться (WARNING: данные будут потеряны!)
    echo   3 - Выйти без обновления
    echo.
    set /p choice="Ваш выбор (1-3): "
    
    if "!choice!"=="1" (
        echo 💾 Сохранение изменений в stash...
        git stash push -m "Auto-stash before update"
        if %ERRORLEVEL% NEQ 0 (
            echo ❌ Ошибка при сохранении в stash!
            pause
            exit /b 1
        )
        set STASHED=1
    ) else if "!choice!"=="2" (
        echo ⚠️ Отмена локальных изменений...
        git reset --hard HEAD
        git clean -fd
        if %ERRORLEVEL% NEQ 0 (
            echo ❌ Ошибка при отмене изменений!
            pause
            exit /b 1
        )
    ) else if "!choice!"=="3" (
        echo Выход без обновления.
        pause
        exit /b 0
    ) else (
        echo Неверный выбор. Выход.
        pause
        exit /b 1
    )
) else (
    echo ✅ Локальные изменения отсутствуют.
)

echo.
echo 📥 Получение обновлений из удалённого репозитория...
git fetch origin
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Ошибка при получении обновлений!
    echo Проверьте подключение к интернету и наличие удалённого репозитория.
    
    if defined STASHED (
        echo 💾 Восстановление изменений из stash...
        git stash pop
    )
    
    pause
    exit /b 1
)

echo.
echo 🔄 Применение обновлений...
FOR /F "tokens=*" %%i IN ('git branch --show-current') DO set CURRENT_BRANCH=%%i
git pull origin %CURRENT_BRANCH%
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Ошибка при применении обновлений!
    echo Возможны конфликты слияния.
    
    if defined STASHED (
        echo 💾 Восстановление изменений из stash...
        git stash pop
    )
    
    echo.
    echo Для разрешения конфликтов выполните вручную:
    echo   git mergetool
    echo   git commit
    pause
    exit /b 1
)

echo.
echo ✅ Обновление успешно завершено!
echo.

REM Восстановление изменений из stash если они были сохранены
if defined STASHED (
    echo 💾 Восстановление локальных изменений...
    git stash pop
    if %ERRORLEVEL% NEQ 0 (
        echo ⚠️ Возможны конфликты при восстановлении stash.
        echo Разрешите их вручную через git mergetool.
    )
)

echo.
echo 📦 Проверка зависимостей...
if exist "requirements.txt" (
    echo Установка/обновление Python-зависимостей...
    
    REM Проверка наличия venv
    if exist "venv\Scripts\activate.bat" (
        echo Активация виртуального окружения...
        call venv\Scripts\activate.bat
        
        pip install -r requirements.txt --upgrade --quiet
        if %ERRORLEVEL% NEQ 0 (
            echo ⚠️ Предупреждение: некоторые зависимости не удалось обновить.
        ) else (
            echo ✅ Зависимости обновлены.
        )
        
        deactivate >nul 2>nul
    ) else (
        echo ⚠️ Виртуальное окружение не найдено.
        echo Запустите Run.bat для создания venv и установки зависимостей.
    )
)

echo.
echo ============================================
echo   🎉 Проект готов к запуску!
echo   Для запуска выполните: Run.bat
echo ============================================
echo.

pause
