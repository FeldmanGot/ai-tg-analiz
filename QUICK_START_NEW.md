# 🚀 Быстрый запуск Telegram Analyzer v2.0

## ⚡ Быстрый запуск

### 1. Автоматический запуск (Windows)
```bash
start_new_system.bat
```

### 2. Ручной запуск

#### Бэкенд:
```bash
cd backend
pip install -r requirements_new.txt
python main_new.py
```

#### Фронтенд:
```bash
cd frontend-new
npm install
npm start
```

## 📱 Доступ к системе

- **Фронтенд**: http://localhost:3000
- **Бэкенд**: http://localhost:8001

## 🔐 Первый запуск

1. **Авторизация**: Введите API ID, API Hash, телефон
2. **Скачивание**: Выберите чат и скачайте историю
3. **Слушание**: Запустите мониторинг новых сообщений

## 📁 Структура файлов

```
├── backend/
│   ├── main_new.py          # Новый бэкенд
│   ├── telegram_analyzer.py # Система анализа
│   └── requirements_new.txt # Зависимости
├── frontend-new/
│   └── src/
│       ├── AppNew.js        # Новый интерфейс
│       └── AppNew.css       # Стили
└── data/                    # Данные (создаётся автоматически)
    ├── sessions/            # Сессии Telegram
    ├── live/               # Сообщения
    ├── media/              # Медиафайлы
    └── profiles/           # Профили
```

## 🎯 Основные функции

- ✅ **Авторизация** в Telegram
- ✅ **Скачивание истории** сообщений
- ✅ **Слушание новых** сообщений
- ✅ **Расшифровка голосовых** через Whisper
- ✅ **Анализ профилей** чатов
- ✅ **Современный интерфейс**

## 🔧 Устранение проблем

### Порт занят:
```bash
# Остановите процессы
taskkill /f /im python.exe
taskkill /f /im node.exe
```

### Ошибки зависимостей:
```bash
pip install --upgrade pip
pip install -r backend/requirements_new.txt
```

### Проблемы с Whisper:
```bash
pip install openai-whisper
```

---

**Готово!** Система полностью переработана с нуля! 🎉 