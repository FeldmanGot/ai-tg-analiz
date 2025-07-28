@echo off
echo ========================================
echo    Установка Ollama для Windows
echo ========================================
echo.

echo Скачивание Ollama...
powershell -Command "Invoke-WebRequest -Uri 'https://ollama.ai/download/ollama-windows-amd64.exe' -OutFile 'ollama.exe'"

echo.
echo Установка Ollama...
ollama.exe install

echo.
echo Запуск Ollama сервера...
start /B ollama serve

echo.
echo Скачивание модели Llama2...
ollama pull llama2

echo.
echo Ollama установлен и запущен!
echo Сервер доступен по адресу: http://localhost:11434
echo.

pause 