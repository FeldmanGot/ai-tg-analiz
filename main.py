#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
import webbrowser
import threading
import time

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Модели данных
class ConfigModel(BaseModel):
    ai_model: str
    telegram_api_key: str
    ollama_url: str = "http://localhost:11434"

class MessageModel(BaseModel):
    chat_id: int
    username: str
    message: str
    timestamp: datetime
    analyzed: bool = False
    summary: Optional[str] = None
    tone: Optional[str] = None
    model_used: Optional[str] = None

class OllamaRequest(BaseModel):
    model: str
    prompt: str
    stream: bool = False
    options: Optional[Dict[str, Any]] = None

# База данных
Base = declarative_base()

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, index=True)
    username = Column(String)
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    analyzed = Column(Boolean, default=False)
    summary = Column(Text, nullable=True)
    tone = Column(String, nullable=True)
    model_used = Column(String, nullable=True)

# Создание базы данных
engine = create_engine("sqlite:///chat_history.db", echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Bot Manager API", version="2.0.0")

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Файл для хранения конфигурации
CONFIG_FILE = Path("config.json")

def load_config():
    """Загрузить конфигурацию из файла"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {
                "ai_model": "llama2",
                "telegram_api_key": "",
                "ollama_url": "http://localhost:11434"
            }
    return {
        "ai_model": "llama2",
        "telegram_api_key": "",
        "ollama_url": "http://localhost:11434"
    }

def save_config(config: dict):
    """Сохранить конфигурацию в файл"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

# Ollama интеграция
class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    
    def generate(self, model: str, prompt: str, options: Optional[Dict] = None) -> Dict:
        """Генерация ответа через Ollama"""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            if options:
                payload["options"] = options
            
            response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return {"error": str(e)}
    
    def list_models(self) -> List[Dict]:
        """Получить список доступных моделей"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            return response.json().get("models", [])
        except Exception as e:
            logger.error(f"Ollama list models error: {e}")
            return []

# Telegram Bot интеграция
class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, chat_id: int, text: str) -> bool:
        """Отправить сообщение в Telegram"""
        try:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            response = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    def get_webhook_info(self) -> Dict:
        """Получить информацию о webhook"""
        try:
            response = requests.get(f"{self.base_url}/getWebhookInfo", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Telegram webhook info error: {e}")
            return {"error": str(e)}

# Глобальные объекты
ollama_client = OllamaClient()
telegram_bot = None

# HTML шаблон с обновленным интерфейсом
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Bot Manager v2.0</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .btn-primary {
            @apply bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-all duration-200 transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2;
        }
        .input-field {
            @apply w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200;
        }
        .card {
            @apply bg-white rounded-xl shadow-lg border border-gray-100 p-6 hover:shadow-xl transition-all duration-300;
        }
        .animate-fade-in {
            animation: fadeIn 0.5s ease-in-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <h1 class="text-2xl font-bold text-gray-900">AI Bot Manager v2.0</h1>
                <div class="flex space-x-2">
                    <button onclick="testOllama()" class="btn-primary">Test Ollama</button>
                    <button onclick="saveConfig()" class="btn-primary" id="saveBtn">Save</button>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- Message -->
        <div id="message" class="hidden mb-6 p-4 rounded-lg"></div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Configuration -->
            <div class="space-y-6">
                <!-- AI Model Selection -->
                <div class="card animate-fade-in">
                    <h2 class="text-xl font-semibold text-gray-900 mb-4">AI Model (Ollama)</h2>
                    <div class="space-y-2">
                        <select id="aiModel" class="input-field">
                            <option value="llama2">Llama2</option>
                            <option value="llama2:7b">Llama2 7B</option>
                            <option value="llama2:13b">Llama2 13B</option>
                            <option value="codellama">CodeLlama</option>
                            <option value="mistral">Mistral</option>
                        </select>
                        <p class="text-sm text-gray-500">Select Ollama model</p>
                    </div>
                </div>

                <!-- Ollama Settings -->
                <div class="card animate-fade-in">
                    <h2 class="text-xl font-semibold text-gray-900 mb-4">Ollama Settings</h2>
                    <div class="space-y-2">
                        <input
                            type="text"
                            id="ollamaUrl"
                            placeholder="http://localhost:11434"
                            class="input-field"
                        />
                        <p class="text-sm text-gray-500">Ollama server URL</p>
                    </div>
                </div>

                <!-- Telegram Settings -->
                <div class="card animate-fade-in">
                    <h2 class="text-xl font-semibold text-gray-900 mb-4">Telegram Settings</h2>
                    <div class="space-y-2">
                        <input
                            type="password"
                            id="telegramApiKey"
                            placeholder="Enter your Telegram API key"
                            class="input-field"
                        />
                        <p class="text-sm text-gray-500">
                            Введите ваш Telegram Bot API ключ
                        </p>
                    </div>
                </div>
            </div>

            <!-- Chat History -->
            <div class="space-y-6">
                <div class="card animate-fade-in">
                    <h2 class="text-xl font-semibold text-gray-900 mb-4">Chat History</h2>
                    <div id="chatHistory" class="space-y-2 max-h-96 overflow-y-auto">
                        <p class="text-sm text-gray-500">Loading chat history...</p>
                    </div>
                </div>

                <!-- System Status -->
                <div class="card animate-fade-in">
                    <h2 class="text-xl font-semibold text-gray-900 mb-4">System Status</h2>
                    <div id="systemStatus" class="space-y-2">
                        <div class="flex items-center space-x-2">
                            <div class="w-3 h-3 bg-gray-400 rounded-full" id="ollamaStatus"></div>
                            <span class="text-sm">Ollama: Checking...</span>
                        </div>
                        <div class="flex items-center space-x-2">
                            <div class="w-3 h-3 bg-gray-400 rounded-full" id="telegramStatus"></div>
                            <span class="text-sm">Telegram: Checking...</span>
                        </div>
                        <div class="flex items-center space-x-2">
                            <div class="w-3 h-3 bg-gray-400 rounded-full" id="dbStatus"></div>
                            <span class="text-sm">Database: Checking...</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="mt-16 bg-white border-t border-gray-200">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <p class="text-center text-sm text-gray-500">
                AI Bot Manager v2.0 - FastAPI + Ollama + SQLite
            </p>
        </div>
    </footer>

    <script>
        // Загрузить конфигурацию при загрузке страницы
        window.addEventListener('load', function() {
            loadConfig();
            loadChatHistory();
            checkSystemStatus();
        });

        async function loadConfig() {
            try {
                const response = await fetch('/api/config');
                const config = await response.json();
                
                document.getElementById('aiModel').value = config.ai_model;
                document.getElementById('ollamaUrl').value = config.ollama_url;
                document.getElementById('telegramApiKey').value = config.telegram_api_key;
            } catch (error) {
                console.error('Error loading config:', error);
            }
        }

        async function saveConfig() {
            const saveBtn = document.getElementById('saveBtn');
            const messageDiv = document.getElementById('message');
            
            saveBtn.textContent = 'Сохранение...';
            saveBtn.disabled = true;
            
            try {
                const config = {
                    ai_model: document.getElementById('aiModel').value,
                    ollama_url: document.getElementById('ollamaUrl').value,
                    telegram_api_key: document.getElementById('telegramApiKey').value
                };

                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(config)
                });

                const result = await response.json();

                if (response.ok) {
                    showMessage('Конфигурация успешно сохранена!', 'success');
                } else {
                    showMessage(result.detail || 'Ошибка сохранения конфигурации', 'error');
                }
            } catch (error) {
                showMessage('Ошибка сохранения конфигурации', 'error');
                console.error('Error saving config:', error);
            } finally {
                saveBtn.textContent = 'Save';
                saveBtn.disabled = false;
            }
        }

        async function testOllama() {
            try {
                const response = await fetch('/api/test-ollama');
                const result = await response.json();
                
                if (response.ok) {
                    showMessage('Ollama подключен успешно!', 'success');
                } else {
                    showMessage(result.detail || 'Ошибка подключения к Ollama', 'error');
                }
            } catch (error) {
                showMessage('Ошибка подключения к Ollama', 'error');
                console.error('Error testing Ollama:', error);
            }
        }

        async function loadChatHistory() {
            try {
                const response = await fetch('/api/chat-history');
                const history = await response.json();
                
                const chatHistoryDiv = document.getElementById('chatHistory');
                if (history.length === 0) {
                    chatHistoryDiv.innerHTML = '<p class="text-sm text-gray-500">Нет сообщений</p>';
                } else {
                    chatHistoryDiv.innerHTML = history.map(msg => `
                        <div class="p-3 bg-gray-50 rounded-lg">
                            <div class="flex justify-between items-start">
                                <span class="font-medium text-sm">${msg.username}</span>
                                <span class="text-xs text-gray-500">${new Date(msg.timestamp).toLocaleString()}</span>
                            </div>
                            <p class="text-sm mt-1">${msg.message}</p>
                            ${msg.analyzed ? `
                                <div class="mt-2 text-xs text-gray-600">
                                    <div>Summary: ${msg.summary || 'N/A'}</div>
                                    <div>Tone: ${msg.tone || 'N/A'}</div>
                                    <div>Model: ${msg.model_used || 'N/A'}</div>
                                </div>
                            ` : ''}
                        </div>
                    `).join('');
                }
            } catch (error) {
                console.error('Error loading chat history:', error);
            }
        }

        async function checkSystemStatus() {
            // Check Ollama
            try {
                const response = await fetch('/api/test-ollama');
                const ollamaStatus = document.getElementById('ollamaStatus');
                if (response.ok) {
                    ollamaStatus.className = 'w-3 h-3 bg-green-500 rounded-full';
                } else {
                    ollamaStatus.className = 'w-3 h-3 bg-red-500 rounded-full';
                }
            } catch (error) {
                document.getElementById('ollamaStatus').className = 'w-3 h-3 bg-red-500 rounded-full';
            }

            // Check Telegram
            try {
                const response = await fetch('/api/test-telegram');
                const telegramStatus = document.getElementById('telegramStatus');
                if (response.ok) {
                    telegramStatus.className = 'w-3 h-3 bg-green-500 rounded-full';
                } else {
                    telegramStatus.className = 'w-3 h-3 bg-red-500 rounded-full';
                }
            } catch (error) {
                document.getElementById('telegramStatus').className = 'w-3 h-3 bg-red-500 rounded-full';
            }

            // Check Database
            try {
                const response = await fetch('/api/test-database');
                const dbStatus = document.getElementById('dbStatus');
                if (response.ok) {
                    dbStatus.className = 'w-3 h-3 bg-green-500 rounded-full';
                } else {
                    dbStatus.className = 'w-3 h-3 bg-red-500 rounded-full';
                }
            } catch (error) {
                document.getElementById('dbStatus').className = 'w-3 h-3 bg-red-500 rounded-full';
            }
        }

        function showMessage(text, type) {
            const messageDiv = document.getElementById('message');
            messageDiv.textContent = text;
            messageDiv.className = `mb-6 p-4 rounded-lg ${
                type === 'success' 
                    ? 'bg-green-100 text-green-800 border border-green-200' 
                    : 'bg-red-100 text-red-800 border border-red-200'
            }`;
            messageDiv.classList.remove('hidden');

            setTimeout(() => {
                messageDiv.classList.add('hidden');
            }, 3000);
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    """Главная страница"""
    return HTML_TEMPLATE

@app.get("/api/config")
async def get_config():
    """Получить конфигурацию"""
    try:
        config = load_config()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки конфигурации: {str(e)}")

@app.post("/api/config")
async def save_config_endpoint(config: ConfigModel):
    """Сохранить конфигурацию"""
    try:
        # Валидация модели ИИ
        valid_models = ["llama2", "llama2:7b", "llama2:13b", "codellama", "mistral"]
        if config.ai_model not in valid_models:
            raise HTTPException(status_code=400, detail="Неверная модель ИИ")
        
        # Валидация Telegram API ключа
        if not config.telegram_api_key.strip():
            raise HTTPException(status_code=400, detail="Telegram API ключ не может быть пустым")
        
        config_dict = config.dict()
        save_config(config_dict)
        
        # Обновить глобальные объекты
        global ollama_client, telegram_bot
        ollama_client = OllamaClient(config.ollama_url)
        telegram_bot = TelegramBot(config.telegram_api_key)
        
        return {"message": "Конфигурация успешно сохранена", "config": config_dict}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения конфигурации: {str(e)}")

@app.get("/api/test-ollama")
async def test_ollama():
    """Тест подключения к Ollama"""
    try:
        models = ollama_client.list_models()
        if models:
            return {"status": "connected", "models": models}
        else:
            return {"status": "no_models", "message": "Ollama доступен, но модели не найдены"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к Ollama: {str(e)}")

@app.get("/api/test-telegram")
async def test_telegram():
    """Тест подключения к Telegram"""
    try:
        if not telegram_bot:
            raise HTTPException(status_code=400, detail="Telegram бот не настроен")
        
        webhook_info = telegram_bot.get_webhook_info()
        return {"status": "connected", "webhook_info": webhook_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к Telegram: {str(e)}")

@app.get("/api/test-database")
async def test_database():
    """Тест подключения к базе данных"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"status": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к базе данных: {str(e)}")

@app.get("/api/chat-history")
async def get_chat_history():
    """Получить историю чатов"""
    try:
        db = SessionLocal()
        messages = db.query(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(50).all()
        db.close()
        
        return [
            {
                "id": msg.id,
                "chat_id": msg.chat_id,
                "username": msg.username,
                "message": msg.message,
                "timestamp": msg.timestamp.isoformat(),
                "analyzed": msg.analyzed,
                "summary": msg.summary,
                "tone": msg.tone,
                "model_used": msg.model_used
            }
            for msg in messages
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки истории чатов: {str(e)}")

@app.post("/api/analyze")
async def analyze_conversation(request: MessageModel):
    """Анализ сообщения через Ollama"""
    try:
        config = load_config()
        
        # Генерируем промпт для анализа
        prompt = f"""
        Проанализируй следующее сообщение и предоставь JSON ответ с полями:
        - summary: краткое резюме (1-2 предложения)
        - tone: тон сообщения (позитивный/негативный/нейтральный)
        
        Сообщение: {request.message}
        
        Ответ в формате JSON:
        """
        
        # Получаем ответ от Ollama
        response = ollama_client.generate(config["ai_model"], prompt)
        
        if "error" in response:
            raise HTTPException(status_code=500, detail=f"Ошибка Ollama: {response['error']}")
        
        # Парсим ответ
        try:
            analysis = json.loads(response.get("response", "{}"))
        except:
            analysis = {
                "summary": "Не удалось проанализировать",
                "tone": "нейтральный"
            }
        
        # Сохраняем в базу данных
        db = SessionLocal()
        chat_message = ChatMessage(
            chat_id=request.chat_id,
            username=request.username,
            message=request.message,
            timestamp=request.timestamp,
            analyzed=True,
            summary=analysis.get("summary"),
            tone=analysis.get("tone"),
            model_used=config["ai_model"]
        )
        db.add(chat_message)
        db.commit()
        db.close()
        
        return {
            "message": "Сообщение проанализировано",
            "analysis": analysis,
            "model_used": config["ai_model"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")

@app.post("/webhook/telegram")
async def telegram_webhook(update: Dict[str, Any]):
    """Webhook для Telegram бота"""
    try:
        if "message" not in update:
            return {"status": "ok"}
        
        message = update["message"]
        chat_id = message["chat"]["id"]
        username = message["from"].get("username", "Unknown")
        text = message.get("text", "")
        
        if not text:
            return {"status": "ok"}
        
        # Сохраняем сообщение в базу данных
        db = SessionLocal()
        chat_message = ChatMessage(
            chat_id=chat_id,
            username=username,
            message=text,
            timestamp=datetime.utcnow(),
            analyzed=False
        )
        db.add(chat_message)
        db.commit()
        db.close()
        
        # Анализируем сообщение
        analysis_request = MessageModel(
            chat_id=chat_id,
            username=username,
            message=text,
            timestamp=datetime.utcnow()
        )
        
        analysis_result = await analyze_conversation(analysis_request)
        
        # Отправляем ответ в Telegram
        if telegram_bot:
            response_text = f"""
📝 <b>Анализ сообщения:</b>

💬 <b>Сообщение:</b> {text}

📋 <b>Резюме:</b> {analysis_result['analysis']['summary']}

🎭 <b>Тон:</b> {analysis_result['analysis']['tone']}

🤖 <b>Модель:</b> {analysis_result['model_used']}
            """
            telegram_bot.send_message(chat_id, response_text)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return {"status": "error", "message": str(e)}

def open_browser():
    """Открыть браузер через 1 секунду"""
    time.sleep(1)
    webbrowser.open('http://localhost:8000')

if __name__ == '__main__':
    print("🚀 Запуск AI Bot Manager v2.0...")
    print("📱 Открытие браузера...")
    
    # Запустить браузер в отдельном потоке
    threading.Thread(target=open_browser, daemon=True).start()
    
    print("🌐 Приложение доступно по адресу: http://localhost:8000")
    print("📋 Функции:")
    print("   - FastAPI + Ollama интеграция")
    print("   - SQLite база данных")
    print("   - Telegram Bot webhook")
    print("   - Анализ сообщений в реальном времени")
    print("\n💡 Для остановки нажмите Ctrl+C")
    
    # Запустить FastAPI приложение
    uvicorn.run(app, host="0.0.0.0", port=8000) 