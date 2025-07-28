@echo off
echo ========================================
echo    AI TG Analiz - Загрузка на GitHub
echo ========================================
echo.

echo Введите ваше имя пользователя GitHub:
set /p GITHUB_USERNAME=

echo.
echo Создаем репозиторий на GitHub...
echo.

echo [1/3] Добавляем удаленный репозиторий...
git remote add origin https://github.com/%GITHUB_USERNAME%/ai-tg-analiz.git

echo [2/3] Переименовываем ветку в main...
git branch -M main

echo [3/3] Отправляем код на GitHub...
git push -u origin main

echo.
echo [4/4] Отправляем тег релиза...
git push origin v1.0.0

echo.
echo ========================================
echo    Загрузка завершена!
echo    Репозиторий: https://github.com/%GITHUB_USERNAME%/ai-tg-analiz
echo ========================================
echo.
echo Теперь:
echo 1. Перейдите на GitHub и настройте репозиторий
echo 2. Добавьте Topics (теги) в настройках
echo 3. Создайте релиз v1.0.0
echo.
pause 