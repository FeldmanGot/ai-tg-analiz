@echo off
echo ========================================
echo    AI TG Analiz - Запуск приложения
echo ========================================
echo.

echo [1/3] Запуск бэкенда...
start "Backend" cmd /k "cd backend && python main.py"

echo [2/3] Ожидание запуска бэкенда...
timeout /t 3 /nobreak > nul

echo [3/3] Запуск фронтенда...
start "Frontend" cmd /k "cd frontend-new && npm start"

echo.
echo ========================================
echo    Приложение запущено!
echo    Бэкенд: http://localhost:8000
echo    Фронтенд: http://localhost:3000
echo ========================================
echo.
echo Нажмите любую клавишу для выхода...
pause > nul 