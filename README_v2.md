# AI Bot Manager v2.0 - FastAPI + Ollama + SQLite

Полнофункциональная система для управления ИИ-ботом с локальной LLM и Telegram интеграцией.

## 🏗️ Архитектура

```
[Telegram API] → [FastAPI HTTP-сервер] → [Ollama LLM] → [SQLite DB] → [JSON/HTML ответ]
```

## 🚀 Быстрый запуск

### 1. Установка Ollama
```bash
# Windows
install_ollama.bat

# Linux/Mac
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama2
```

### 2. Запуск приложения
```bash
# Windows
start.bat

# Linux/Mac
pip install -r requirements.txt
python main.py
```

## 📋 Функции

### ✅ Реализовано
- **FastAPI** - высокопроизводительный HTTP сервер
- **Ollama интеграция** - локальная LLM (Llama2, CodeLlama, Mistral)
- **SQLite база данных** - хранение истории чатов
- **Telegram Bot** - webhook для обработки сообщений
- **Веб-интерфейс** - управление и мониторинг
- **Анализ в реальном времени** - summary, tone, model tracking

### 📊 Структура базы данных
```sql
chat_messages:
- id (Primary Key)
- chat_id (Telegram chat ID)
- username (Telegram username)
- message (Текст сообщения)
- timestamp (Время сообщения)
- analyzed (Проанализировано ли)
- summary (Краткое резюме)
- tone (Тон сообщения)
- model_used (Использованная модель)
```

## 🔧 Технические требования

### Система
- **GPU**: RTX 4060 (рекомендуется)
- **RAM**: 32 ГБ ОЗУ
- **OS**: Windows 10/11, Linux, macOS

### Программное обеспечение
- **Python 3.9+**
- **Ollama** (локальная LLM)
- **SQLite** (встроенная)
- **Telegram Bot Token**

## 🌐 API Endpoints

### Конфигурация
- `GET /api/config` - получить конфигурацию
- `POST /api/config` - сохранить конфигурацию

### Тестирование
- `GET /api/test-ollama` - тест Ollama подключения
- `GET /api/test-telegram` - тест Telegram подключения
- `GET /api/test-database` - тест базы данных

### Данные
- `GET /api/chat-history` - история чатов
- `POST /api/analyze` - анализ сообщения

### Telegram
- `POST /webhook/telegram` - webhook для Telegram

## 📱 Telegram Bot настройка

1. **Создайте бота** через @BotFather
2. **Получите токен** и добавьте в конфигурацию
3. **Настройте webhook**:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://your-domain.com/webhook/telegram
   ```

## 🎛️ Управление моделями

### Доступные модели Ollama
- `llama2` - базовая модель
- `llama2:7b` - 7B параметров
- `llama2:13b` - 13B параметров
- `codellama` - для программирования
- `mistral` - быстрая модель

### Установка новых моделей
```bash
ollama pull llama2:7b
ollama pull codellama
ollama pull mistral
```

## 📊 Мониторинг

### Веб-интерфейс
- **Статус систем** - Ollama, Telegram, Database
- **История чатов** - последние 50 сообщений
- **Анализ сообщений** - summary, tone, модель
- **Конфигурация** - настройки в реальном времени

### Логи
- **FastAPI** - HTTP запросы
- **Ollama** - генерация ответов
- **Telegram** - webhook события
- **SQLite** - операции с базой данных

## 🔮 Будущие функции

🔄 **Расширенный анализ** - sentiment, entities, keywords  
🔄 **Множественные модели** - переключение между LLM  
🔄 **Групповые чаты** - анализ групповых переписок  
🔄 **Экспорт данных** - CSV, JSON, PDF отчеты  
🔄 **API документация** - Swagger/OpenAPI  

## 🛠️ Разработка

### Структура проекта
```
ai-bot-manager/
├── main.py              # FastAPI приложение
├── requirements.txt     # Python зависимости
├── install_ollama.bat  # Установка Ollama
├── start.bat           # Запуск приложения
├── chat_history.db     # SQLite база данных
├── config.json         # Конфигурация
└── README_v2.md        # Документация
```

### Добавление новых функций
1. **Новые эндпоинты** - в `main.py`
2. **Модели данных** - в Pydantic классах
3. **База данных** - в SQLAlchemy моделях
4. **Веб-интерфейс** - в HTML_TEMPLATE

## 📈 Производительность

### RTX 4060 + 32GB RAM
- **Генерация**: ~10-30 токенов/сек
- **Анализ**: ~1-3 секунды на сообщение
- **Память**: ~8-16GB для моделей
- **Параллельность**: до 10 одновременных запросов

### Оптимизация
- **Модель**: llama2:7b для скорости
- **Контекст**: ограничение до 2048 токенов
- **Кэширование**: частых запросов
- **База данных**: индексы для быстрого поиска

## 🚨 Устранение неполадок

### Ollama не запускается
```bash
# Проверка статуса
ollama list

# Перезапуск
ollama serve
```

### Telegram webhook ошибки
```bash
# Проверка webhook
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo
```

### База данных недоступна
```bash
# Проверка файла
ls -la chat_history.db

# Пересоздание
rm chat_history.db
python main.py
```

Приложение готово к использованию! 🎉 