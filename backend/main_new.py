#!/usr/bin/env python3
"""
Новый основной файл бэкенда с системой анализа Telegram
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Импортируем нашу систему анализа
from telegram_analyzer import TelegramAnalyzer

app = FastAPI(title="Telegram Analyzer API", version="2.0")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальные переменные
telegram_analyzer = None
active_chats = {}

# Модели данных
class TelegramAuthRequest(BaseModel):
    api_id: int
    api_hash: str
    phone: str

class TelegramCodeRequest(BaseModel):
    code: str
    password: Optional[str] = None

class ChatRequest(BaseModel):
    chat: str
    limit: int = 3000

class AnalysisRequest(BaseModel):
    chat: str
    messages_count: int = 30

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    print("🚀 Запуск Telegram Analyzer API v2.0")

@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "Telegram Analyzer API v2.0",
        "status": "running",
        "endpoints": {
            "/telegram/connect": "Подключение и отправка кода",
            "/telegram/verify": "Ввод кода и пароля",
            "/telegram/download": "Скачивание истории чата",
            "/telegram/listen": "Слушание новых сообщений",
            "/telegram/profile": "Получение профиля чата",
            "/telegram/analysis": "Анализ сообщений"
        }
    }

@app.post("/telegram/connect")
async def telegram_connect(data: TelegramAuthRequest):
    """Подключение к Telegram и отправка кода"""
    global telegram_analyzer
    
    try:
        telegram_analyzer = TelegramAnalyzer(
            api_id=data.api_id,
            api_hash=data.api_hash,
            phone=data.phone
        )
        
        # Подключаемся
        if not await telegram_analyzer.connect():
            raise HTTPException(status_code=400, detail="Ошибка подключения")
        
        # Проверяем авторизацию
        if await telegram_analyzer.check_auth():
            return {
                "status": "already_authorized",
                "message": "Уже авторизован"
            }
        
        # Отправляем код
        if await telegram_analyzer.send_code():
            return {
                "status": "code_sent",
                "message": "Код отправлен на телефон"
            }
        else:
            raise HTTPException(status_code=400, detail="Ошибка отправки кода")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка: {str(e)}")

@app.post("/telegram/verify")
async def telegram_verify(data: TelegramCodeRequest):
    """Проверка кода и пароля"""
    global telegram_analyzer
    
    if not telegram_analyzer:
        raise HTTPException(status_code=400, detail="Сначала выполните подключение")
    
    try:
        result = await telegram_analyzer.sign_in(data.code, data.password)
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": "Авторизация успешна"
            }
        elif result["status"] == "2fa_required":
            return {
                "status": "2fa_required",
                "message": "Требуется пароль для двухфакторной аутентификации"
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Ошибка авторизации"))
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка: {str(e)}")

@app.post("/telegram/download")
async def download_chat_history(data: ChatRequest):
    """Скачивает историю чата"""
    global telegram_analyzer
    
    if not telegram_analyzer:
        raise HTTPException(status_code=400, detail="Сначала выполните авторизацию")
    
    try:
        success = await telegram_analyzer.download_history(data.chat, data.limit)
        
        if success:
            return {
                "status": "success",
                "message": f"История чата {data.chat} скачана",
                "chat": data.chat,
                "limit": data.limit
            }
        else:
            raise HTTPException(status_code=500, detail="Ошибка скачивания истории")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка: {str(e)}")

@app.post("/telegram/listen")
async def start_listening(data: ChatRequest, background_tasks: BackgroundTasks):
    """Запускает слушание новых сообщений"""
    global telegram_analyzer, active_chats
    
    if not telegram_analyzer:
        raise HTTPException(status_code=400, detail="Сначала выполните авторизацию")
    
    try:
        # Добавляем в активные чаты
        active_chats[data.chat] = {
            "started_at": datetime.now().isoformat(),
            "status": "listening"
        }
        
        # Запускаем слушание в фоне
        background_tasks.add_task(telegram_analyzer.listen_to_new_messages, data.chat)
        
        return {
            "status": "success",
            "message": f"Слушание чата {data.chat} запущено",
            "chat": data.chat
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка: {str(e)}")

@app.get("/telegram/profile/{chat}")
async def get_chat_profile(chat: str):
    """Получает профиль чата"""
    try:
        # Определяем ключ чата
        if chat.startswith('@'):
            chat_key = chat
        else:
            chat_key = f"chat_{chat}"
        
        profile_file = f"data/profiles/{chat_key}_profile.json"
        analysis_file = f"data/profiles/{chat_key}_last_analysis.txt"
        
        profile = {}
        analysis = ""
        
        # Загружаем профиль
        if os.path.exists(profile_file):
            with open(profile_file, 'r', encoding='utf-8') as f:
                profile = json.load(f)
        
        # Загружаем последний анализ
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r', encoding='utf-8') as f:
                analysis = f.read()
        
        return {
            "status": "success",
            "chat": chat,
            "profile": profile,
            "last_analysis": analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка: {str(e)}")

@app.get("/telegram/messages/{chat}")
async def get_chat_messages(chat: str, limit: int = 50):
    """Получает сообщения чата"""
    try:
        # Определяем ключ чата
        if chat.startswith('@'):
            chat_key = chat
        else:
            chat_key = f"chat_{chat}"
        
        live_file = f"data/live/{chat_key}.json"
        
        if os.path.exists(live_file):
            with open(live_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            # Возвращаем последние сообщения
            recent_messages = messages[-limit:] if len(messages) > limit else messages
            
            return {
                "status": "success",
                "chat": chat,
                "total_messages": len(messages),
                "recent_messages": recent_messages
            }
        else:
            return {
                "status": "not_found",
                "message": f"Файл с сообщениями для {chat} не найден"
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка: {str(e)}")

@app.get("/telegram/active")
async def get_active_chats():
    """Получает список активных чатов"""
    return {
        "status": "success",
        "active_chats": active_chats
    }

@app.delete("/telegram/stop/{chat}")
async def stop_listening(chat: str):
    """Останавливает слушание чата"""
    global active_chats
    
    if chat in active_chats:
        del active_chats[chat]
        return {
            "status": "success",
            "message": f"Слушание чата {chat} остановлено"
        }
    else:
        return {
            "status": "not_found",
            "message": f"Чат {chat} не найден в активных"
        }

@app.get("/telegram/files")
async def list_files():
    """Получает список файлов"""
    try:
        files = {
            "live": [],
            "profiles": [],
            "media": []
        }
        
        # Список live файлов
        if os.path.exists("data/live"):
            for file in os.listdir("data/live"):
                if file.endswith('.json'):
                    files["live"].append(file)
        
        # Список профилей
        if os.path.exists("data/profiles"):
            for file in os.listdir("data/profiles"):
                if file.endswith('.json'):
                    files["profiles"].append(file)
        
        # Список медиафайлов
        if os.path.exists("data/media"):
            for file in os.listdir("data/media"):
                files["media"].append(file)
        
        return {
            "status": "success",
            "files": files
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001) 