# AI TG Analiz - Загрузка на GitHub
Write-Host "========================================" -ForegroundColor Green
Write-Host "   AI TG Analiz - Загрузка на GitHub" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Запрашиваем имя пользователя GitHub
$githubUsername = Read-Host "Введите ваше имя пользователя GitHub"

if (-not $githubUsername) {
    Write-Host "❌ Имя пользователя не указано!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🔍 Проверяем Git статус..." -ForegroundColor Yellow
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "⚠️  Есть несохраненные изменения!" -ForegroundColor Yellow
    $commit = Read-Host "Хотите зафиксировать изменения? (y/n)"
    if ($commit -eq "y" -or $commit -eq "Y") {
        git add .
        git commit -m "Auto-commit before GitHub upload"
    }
}

Write-Host ""
Write-Host "📤 Начинаем загрузку на GitHub..." -ForegroundColor Yellow

try {
    # Добавляем удаленный репозиторий
    Write-Host "[1/4] Добавляем удаленный репозиторий..." -ForegroundColor Cyan
    git remote add origin "https://github.com/$githubUsername/ai-tg-analiz.git"
    
    # Переименовываем ветку в main
    Write-Host "[2/4] Переименовываем ветку в main..." -ForegroundColor Cyan
    git branch -M main
    
    # Отправляем код
    Write-Host "[3/4] Отправляем код на GitHub..." -ForegroundColor Cyan
    git push -u origin main
    
    # Отправляем тег релиза
    Write-Host "[4/4] Отправляем тег релиза v1.0.0..." -ForegroundColor Cyan
    git push origin v1.0.0
    
    Write-Host ""
    Write-Host "✅ Загрузка завершена успешно!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "📁 Репозиторий: https://github.com/$githubUsername/ai-tg-analiz" -ForegroundColor Cyan
    Write-Host "🏷️  Тег: v1.0.0" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Green
    
    # Открываем репозиторий в браузере
    $openBrowser = Read-Host "Открыть репозиторий в браузере? (y/n)"
    if ($openBrowser -eq "y" -or $openBrowser -eq "Y") {
        Start-Process "https://github.com/$githubUsername/ai-tg-analiz"
    }
    
} catch {
    Write-Host "❌ Ошибка при загрузке: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Возможные причины:" -ForegroundColor Yellow
    Write-Host "1. Репозиторий не создан на GitHub" -ForegroundColor Yellow
    Write-Host "2. Неправильное имя пользователя" -ForegroundColor Yellow
    Write-Host "3. Проблемы с аутентификацией" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Создайте репозиторий на GitHub:" -ForegroundColor Cyan
    Write-Host "1. Перейдите на https://github.com/new" -ForegroundColor Cyan
    Write-Host "2. Название: ai-tg-analiz" -ForegroundColor Cyan
    Write-Host "3. Описание: 🤖 Интеллектуальный анализатор Telegram переписок с поддержкой ИИ" -ForegroundColor Cyan
    Write-Host "4. НЕ ставьте галочки на README, .gitignore, license" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Нажмите любую клавишу для выхода..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 