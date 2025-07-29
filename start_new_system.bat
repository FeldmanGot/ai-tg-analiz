@echo off
echo 🤖 Запуск Telegram Analyzer v2.0
echo.

echo [1/3] Установка зависимостей бэкенда...
cd backend
pip install -r requirements_new.txt
if %errorlevel% neq 0 (
    echo ❌ Ошибка установки зависимостей бэкенда
    pause
    exit /b 1
)

echo [2/3] Установка зависимостей фронтенда...
cd ..\frontend-new
npm install
if %errorlevel% neq 0 (
    echo ❌ Ошибка установки зависимостей фронтенда
    pause
    exit /b 1
)

echo [3/3] Запуск системы...
echo.
echo 🚀 Запуск бэкенда на http://localhost:8001
start "Backend" cmd /k "cd backend && python main_new.py"

echo ⏳ Ожидание запуска бэкенда...
timeout /t 5 /nobreak > nul

echo 🎨 Запуск фронтенда на http://localhost:3000
start "Frontend" cmd /k "cd frontend-new && npm start"

echo.
echo ✅ Система запущена!
echo 📱 Фронтенд: http://localhost:3000
echo 🔧 Бэкенд: http://localhost:8001
echo.
echo 💡 Для остановки закройте окна командной строки
pause 