# Инструкции по установке и запуску AI Bot Manager

## Требования

- Python 3.9+
- Node.js 18+
- npm или yarn

## Быстрый запуск

### Вариант 1: Docker (рекомендуется)

```bash
# Запуск всего приложения
docker-compose up

# Приложение будет доступно по адресам:
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
```

### Вариант 2: Локальная установка

#### 1. Запуск Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Запуск Frontend

```bash
cd frontend
npm install
npm start
```

### Вариант 3: Windows (bat файлы)

1. Запустите `start-backend.bat` для запуска backend
2. Запустите `start-frontend.bat` для запуска frontend

## Структура проекта

```
ai-bot-manager/
├── backend/                 # FastAPI backend
│   ├── main.py             # Основной файл API
│   ├── requirements.txt    # Python зависимости
│   └── Dockerfile         # Docker конфигурация
├── frontend/               # React frontend
│   ├── src/
│   │   ├── App.js         # Главный компонент
│   │   ├── index.js       # Точка входа
│   │   └── index.css      # Стили
│   ├── package.json       # Node.js зависимости
│   └── Dockerfile         # Docker конфигурация
├── docker-compose.yml      # Docker Compose
└── README.md              # Документация
```

## API Endpoints

### Backend API (http://localhost:8000)

- `GET /` - Информация об API
- `GET /config` - Получить текущую конфигурацию
- `POST /config` - Сохранить конфигурацию
- `POST /analyze` - Анализ переписки (заглушка)
- `GET /health` - Проверка здоровья API

### Примеры запросов

```bash
# Получить конфигурацию
curl http://localhost:8000/config

# Сохранить конфигурацию
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{"ai_model": "gpt-4", "telegram_api_key": "your-api-key"}'
```

## Функциональность

### ✅ Реализовано
- Выбор модели ИИ (GPT-3.5, GPT-4, GPT-4o)
- Настройка Telegram API ключа
- Сохранение конфигурации в JSON файл
- Современный адаптивный дизайн
- CORS поддержка
- Docker контейнеризация

### 🔄 В разработке
- Загрузка переписок (JSON, .txt)
- NLP анализ (токенизация, sentiment, резюме)
- Telegram API интеграция
- Анализ чатов

## Устранение неполадок

### Backend не запускается
1. Проверьте версию Python (должна быть 3.9+)
2. Установите зависимости: `pip install -r requirements.txt`
3. Проверьте, что порт 8000 свободен

### Frontend не запускается
1. Проверьте версию Node.js (должна быть 18+)
2. Установите зависимости: `npm install`
3. Проверьте, что порт 3000 свободен

### CORS ошибки
1. Убедитесь, что backend запущен на порту 8000
2. Проверьте настройки CORS в `backend/main.py`

### Docker проблемы
1. Убедитесь, что Docker установлен
2. Проверьте, что порты 3000 и 8000 свободны
3. Пересоберите образы: `docker-compose build`

## Разработка

### Добавление новых функций

1. **Backend**: Добавьте новые эндпоинты в `backend/main.py`
2. **Frontend**: Создайте новые компоненты в `frontend/src/`
3. **API**: Обновите модели данных в `backend/main.py`

### Тестирование

```bash
# Backend тесты
cd backend
python -m pytest

# Frontend тесты
cd frontend
npm test
```

## Лицензия

MIT License 