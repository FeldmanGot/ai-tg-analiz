@echo off
echo ========================================
echo    AI Bot Manager v2.0 - Запуск
echo ========================================
echo.

echo Установка зависимостей...
pip install -r requirements.txt

echo.
echo Проверка Ollama...
ollama list

echo.
echo Запуск приложения...
echo Приложение откроется в браузере автоматически
echo Для остановки нажмите Ctrl+C
echo.

python main.py

pause 