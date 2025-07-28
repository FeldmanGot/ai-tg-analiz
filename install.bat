@echo off
echo ========================================
echo    AI TG Analiz - Установка зависимостей
echo ========================================
echo.

echo [1/3] Установка Python зависимостей...
cd backend
pip install -r requirements.txt
cd ..

echo [2/3] Установка Node.js зависимостей...
cd frontend-new
npm install
cd ..

echo [3/3] Проверка установки...
echo.
echo Проверка Python зависимостей:
python -c "import fastapi, telethon; print('✅ Python зависимости установлены')"

echo.
echo Проверка Node.js зависимостей:
cd frontend-new
npm list --depth=0
cd ..

echo.
echo ========================================
echo    Установка завершена!
echo    Запустите start.bat для запуска приложения
echo ========================================
echo.
pause 