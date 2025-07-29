from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from fastapi import Request
import asyncio
import shutil
import hashlib
from datetime import datetime

# Импортируем функцию анализа
from services.llm import analyze_text

app = FastAPI(title="AI Bot Manager API", version="1.0.0")

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модели данных
class ConfigModel(BaseModel):
    ai_model: str
    telegram_api_key: str

class AnalyzeRequest(BaseModel):
    text: str
    model: str

# Файл для хранения конфигурации
CONFIG_FILE = Path("config.json")

def load_config():
    """Загрузить конфигурацию из файла"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"ai_model": "gpt-3.5-turbo", "telegram_api_key": ""}
    return {"ai_model": "gpt-3.5-turbo", "telegram_api_key": ""}

def save_config(config: dict):
    """Сохранить конфигурацию в файл"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {"message": "AI Bot Manager API", "version": "1.0.0"}

@app.get("/config")
async def get_config():
    """Получить текущую конфигурацию"""
    try:
        config = load_config()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки конфигурации: {str(e)}")

@app.post("/config")
async def save_config_endpoint(config: ConfigModel):
    """Сохранить конфигурацию"""
    try:
        # Валидация модели ИИ
        valid_models = ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]
        if config.ai_model not in valid_models:
            raise HTTPException(status_code=400, detail="Неверная модель ИИ")
        
        # Валидация Telegram API ключа
        if not config.telegram_api_key.strip():
            raise HTTPException(status_code=400, detail="Telegram API ключ не может быть пустым")
        
        config_dict = config.dict()
        save_config(config_dict)
        
        return {"message": "Конфигурация успешно сохранена", "config": config_dict}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения конфигурации: {str(e)}")

@app.post("/analyze")
async def analyze_conversation(request: AnalyzeRequest):
    """Анализ переписки (заглушка для будущего функционала)"""
    try:
        # Здесь будет логика анализа переписки
        return {
            "message": "Анализ переписки",
            "conversation_length": len(request.conversation),
            "status": "pending_implementation"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")

@app.post("/api/analyze")
async def analyze_api(request: AnalyzeRequest):
    """Анализ текста с помощью Ollama"""
    try:
        result = await analyze_text(request.text, request.model)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")

@app.get("/health")
async def health_check():
    """Проверка здоровья API"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

# Пути для сохранения файлов
TELETHON_SESSION_DIR = "telegram_sessions"
MEDIA_DOWNLOAD_DIR = "telegram_media"  # В корне проекта
LLM_EXPORT_DIR = "llm_exports"  # В папке backend

# Создаём папки
os.makedirs(TELETHON_SESSION_DIR, exist_ok=True)
os.makedirs(MEDIA_DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LLM_EXPORT_DIR, exist_ok=True)

# Удаляем TELETHON_CLIENTS, TWOFA_PENDING, PHONE_CODE_HASHES
PHONE_CODE_HASHES = {}

# Глобальные переменные для отслеживания статуса
DOWNLOAD_STATUS = {}
EXPORT_STATUS = {}

def get_session_path(api_id, phone):
    """Создаём уникальное имя сессии на основе api_id и phone"""
    user_hash = hashlib.md5(f"{api_id}_{phone}".encode()).hexdigest()
    sessions_dir = os.path.join(TELETHON_SESSION_DIR, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    return os.path.join(sessions_dir, f"{user_hash}.session")

def get_user_data_path():
    """Файл для хранения данных пользователей"""
    return os.path.join(TELETHON_SESSION_DIR, "users.json")

def save_user_data(api_id, api_hash, phone):
    """Сохраняем данные пользователя для быстрого входа"""
    users_file = get_user_data_path()
    users = []
    if os.path.exists(users_file):
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
        except Exception:
            users = []
    
    # Проверяем, есть ли уже такой пользователь
    user_exists = False
    for user in users:
        if user.get('api_id') == api_id and user.get('phone') == phone:
            user_exists = True
            break
    
    if not user_exists:
        users.append({
            'api_id': api_id,
            'api_hash': api_hash,
            'phone': phone
        })
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)

def get_saved_users():
    """Получаем список сохранённых пользователей"""
    users_file = get_user_data_path()
    if os.path.exists(users_file):
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def remove_user_data(api_id, phone):
    """Удаляем данные пользователя и его сессию"""
    users_file = get_user_data_path()
    users = []
    if os.path.exists(users_file):
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
        except Exception:
            users = []
    
    # Удаляем пользователя из списка
    users = [user for user in users if not (user.get('api_id') == api_id and user.get('phone') == phone)]
    
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    
    # Удаляем файл сессии
    session_path = get_session_path(api_id, phone)
    if os.path.exists(session_path):
        try:
            os.remove(session_path)
        except Exception:
            pass

def get_media_path(chat_id, chat_title):
    """Создаём путь для сохранения медиафайлов чата"""
    # Очищаем название чата от недопустимых символов
    safe_title = "".join(c for c in chat_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_title = safe_title.replace(' ', '_')
    chat_dir = os.path.join(MEDIA_DOWNLOAD_DIR, f"{chat_id}_{safe_title}")
    os.makedirs(chat_dir, exist_ok=True)
    return chat_dir

async def download_media_file(client, message, media_path, file_type):
    """Скачивает медиафайл и возвращает информацию о нём"""
    try:
        os.makedirs(media_path, exist_ok=True)
        date_str = message.date.strftime("%Y%m%d_%H%M%S")
        if file_type == "voice" and message.voice:
            file_path = os.path.join(media_path, f"voice_{date_str}_{message.id}.ogg")
            if not os.path.exists(file_path):
                await client.download_media(message.voice, file_path)
            return {
                "id": message.id,
                "type": "voice",
                "file_path": file_path,
                "date": str(message.date),
                "duration": getattr(message.voice, 'duration', None)
            }
        elif file_type == "video" and message.video:
            file_path = os.path.join(media_path, f"video_{date_str}_{message.id}.mp4")
            if not os.path.exists(file_path):
                await client.download_media(message.video, file_path)
            return {
                "id": message.id,
                "type": "video",
                "file_path": file_path,
                "date": str(message.date),
                "duration": getattr(message.video, 'duration', None),
                "width": getattr(message.video, 'width', None),
                "height": getattr(message.video, 'height', None)
            }
        elif file_type == "video" and message.document and message.document.mime_type and 'video' in message.document.mime_type:
            file_path = os.path.join(media_path, f"video_{date_str}_{message.id}.mp4")
            if not os.path.exists(file_path):
                await client.download_media(message.document, file_path)
            return {
                "id": message.id,
                "type": "video",
                "file_path": file_path,
                "date": str(message.date),
                "mime_type": message.document.mime_type
            }
        elif file_type == "photo" and message.photo:
            file_path = os.path.join(media_path, f"photo_{date_str}_{message.id}.jpg")
            if not os.path.exists(file_path):
                await client.download_media(message.photo, file_path)
            return {
                "id": message.id,
                "type": "photo",
                "file_path": file_path,
                "date": str(message.date),
                "width": getattr(message.photo, 'width', None),
                "height": getattr(message.photo, 'height', None)
            }
        elif file_type == "text" and message.text:
            text_file = os.path.join(media_path, f"text_{date_str}_{message.id}.txt")
            if not os.path.exists(text_file):
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(f"ID: {message.id}\n")
                    f.write(f"Дата: {message.date}\n")
                    f.write(f"Отправитель: {message.sender_id}\n")
                    f.write(f"Текст:\n{message.text}\n")
                    f.write("-" * 50 + "\n")
            return {
                "id": message.id,
                "type": "text",
                "file_path": text_file,
                "date": str(message.date),
                "text_length": len(message.text) if message.text else 0
            }
    except Exception as e:
        print(f"Ошибка скачивания файла {message.id}: {e}")
        return None
    return None

class TelegramLoginRequest(BaseModel):
    api_id: int
    api_hash: str
    phone: str

class TelegramCodeRequest(BaseModel):
    api_id: int
    api_hash: str
    phone: str
    code: str

@app.post("/telegram/login")
async def telegram_login(data: TelegramLoginRequest):
    session_path = get_session_path(data.api_id, data.phone)
    try:
        client = TelegramClient(session_path, data.api_id, data.api_hash)
        await client.connect()
        if await client.is_user_authorized():
            dialogs = []
            async for dialog in client.iter_dialogs():
                dialogs.append({
                    "id": dialog.id,
                    "title": dialog.name,
                    "is_group": dialog.is_group,
                    "is_channel": dialog.is_channel,
                    "is_user": dialog.is_user
                })
            await client.disconnect()
            save_user_data(data.api_id, data.api_hash, data.phone)
            return {"status": "already_authorized", "chats": dialogs}
        sent = await client.send_code_request(data.phone)
        PHONE_CODE_HASHES[f"{data.api_id}_{data.phone}"] = sent.phone_code_hash
        await client.disconnect()
        return {"status": "code_sent"}
    except Exception as e:
        await client.disconnect()
        # Если сессия повреждена — удаляем файл
        if os.path.exists(session_path):
            try:
                os.remove(session_path)
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=f"Login error: {str(e)}")

@app.post("/telegram/code")
async def telegram_code(data: TelegramCodeRequest):
    session_path = get_session_path(data.api_id, data.phone)
    try:
        client = TelegramClient(session_path, data.api_id, data.api_hash)
        await client.connect()
        phone_code_hash = PHONE_CODE_HASHES.get(f"{data.api_id}_{data.phone}")
        if not phone_code_hash:
            await client.disconnect()
            raise HTTPException(status_code=400, detail="No phone_code_hash found. Please login again.")
        try:
            await client.sign_in(data.phone, code=data.code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            await client.disconnect()
            return {"status": "2fa_required", "require_password": True}
        if await client.is_user_authorized():
            dialogs = []
            async for dialog in client.iter_dialogs():
                dialogs.append({
                    "id": dialog.id,
                    "title": dialog.name,
                    "is_group": dialog.is_group,
                    "is_channel": dialog.is_channel,
                    "is_user": dialog.is_user
                })
            await client.disconnect()
            save_user_data(data.api_id, data.api_hash, data.phone)
            return {"status": "authorized", "chats": dialogs}
        else:
            await client.disconnect()
            raise HTTPException(status_code=401, detail="2FA required, not implemented")
    except Exception as e:
        await client.disconnect()
        if os.path.exists(session_path):
            try:
                os.remove(session_path)
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=f"Code error: {str(e)}")

class TelegramPasswordRequest(BaseModel):
    api_id: int
    api_hash: str
    phone: str
    password: str

class TelegramDownloadRequest(BaseModel):
    api_id: int
    api_hash: str
    phone: str

@app.post("/telegram/password")
async def telegram_password(data: TelegramPasswordRequest):
    session_path = get_session_path(data.api_id, data.phone)
    try:
        client = TelegramClient(session_path, data.api_id, data.api_hash)
        await client.connect()
        await client.sign_in(password=data.password)
        dialogs = []
        async for dialog in client.iter_dialogs():
            dialogs.append({
                "id": dialog.id,
                "title": dialog.name,
                "is_group": dialog.is_group,
                "is_channel": dialog.is_channel,
                "is_user": dialog.is_user
            })
        await client.disconnect()
        save_user_data(data.api_id, data.api_hash, data.phone)
        return {"status": "authorized", "chats": dialogs}
    except Exception as e:
        await client.disconnect()
        if os.path.exists(session_path):
            try:
                os.remove(session_path)
            except Exception:
                pass
        raise HTTPException(status_code=401, detail=f"Password error: {str(e)}")

@app.get("/telegram/users")
async def get_telegram_users():
    """Получить список сохранённых пользователей"""
    return get_saved_users()

@app.delete("/telegram/reset")
async def reset_telegram_session(api_id: int, phone: str):
    """Удалить сессию и данные пользователя"""
    try:
        remove_user_data(api_id, phone)
        return {"status": "session_reset", "message": "Сессия и данные пользователя удалены"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset error: {str(e)}")

@app.get("/telegram/chats")
async def telegram_chats(api_id: int, api_hash: str, phone: str):
    session_path = get_session_path(api_id, phone)
    client = None
    try:
        client = TelegramClient(session_path, api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            raise HTTPException(status_code=401, detail="Not authorized")
        dialogs = []
        async for dialog in client.iter_dialogs():
            dialogs.append({
                "id": dialog.id,
                "title": dialog.name,
                "is_group": dialog.is_group,
                "is_channel": dialog.is_channel,
                "is_user": dialog.is_user
            })
        return dialogs
    except Exception as e:
        print(f"Ошибка получения чатов: {e}")
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass
        raise HTTPException(status_code=401, detail=f"Session error: {str(e)}. Please login again.")
    finally:
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass

@app.get("/telegram/chat/{chat_id}/messages")
async def telegram_chat_messages(chat_id: int, api_id: int, api_hash: str, phone: str, limit: int = 20):
    session_path = get_session_path(api_id, phone)
    try:
        client = TelegramClient(session_path, api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            raise HTTPException(status_code=401, detail="Not authorized")
        messages = []
        async for message in client.iter_messages(chat_id, limit=limit):
            messages.append({
                "id": message.id,
                "date": str(message.date),
                "text": message.text,
                "sender_id": message.sender_id
            })
        await client.disconnect()
        return messages
    except Exception as e:
        await client.disconnect()
        if os.path.exists(session_path):
            try:
                os.remove(session_path)
            except Exception:
                pass
        raise HTTPException(status_code=401, detail=f"Session error: {str(e)}. Please login again.")

@app.get("/telegram/download-status/{chat_id}")
async def get_download_status(chat_id: int):
    """Получить статус скачивания для чата"""
    status_key = f"chat_{chat_id}"
    if status_key in DOWNLOAD_STATUS:
        return DOWNLOAD_STATUS[status_key]
    return {"status": "not_found"}

@app.get("/telegram/export-status/{chat_id}")
async def get_export_status(chat_id: int):
    """Получить статус экспорта LLM для чата"""
    status_key = f"export_{chat_id}"
    if status_key in EXPORT_STATUS:
        return EXPORT_STATUS[status_key]
    return {"status": "not_found"}

@app.post("/telegram/chat/{chat_id}/download")
async def download_chat_media(chat_id: int, data: TelegramDownloadRequest, download_voice: bool = True, download_video: bool = True):
    """Скачивает медиафайлы из чата"""
    print(f"🔍 Начинаем скачивание для чата {chat_id}")
    print(f"📱 Параметры: voice={download_voice}, video={download_video}")
    
    # Инициализируем статус
    status_key = f"chat_{chat_id}"
    DOWNLOAD_STATUS[status_key] = {
        "status": "downloading",
        "processed": 0,
        "total": 0,
        "text_count": 0,
        "voice_count": 0,
        "video_count": 0,
        "progress": 0
    }
    
    session_path = get_session_path(data.api_id, data.phone)
    client = None
    try:
        client = TelegramClient(session_path, data.api_id, data.api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            raise HTTPException(status_code=401, detail="Not authorized")
        
        # Получаем информацию о чате
        try:
            chat = await client.get_entity(chat_id)
            chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Unknown')
            print(f"📋 Чат: {chat_title}")
        except Exception:
            chat_title = f"Chat_{chat_id}"
            print(f"⚠️ Не удалось получить название чата, используем: {chat_title}")
        
        media_path = get_media_path(chat_id, chat_title)
        downloaded_files = []
        total_size_mb = 0
        
        print(f"📁 Папка для сохранения: {media_path}")
        
        # Сначала подсчитаем общее количество сообщений
        total_messages = 0
        async for _ in client.iter_messages(chat_id):
            total_messages += 1
        
        print(f"📊 Всего сообщений в чате: {total_messages}")
        
        # Обновляем статус
        DOWNLOAD_STATUS[status_key]["total"] = total_messages
        
        # Скачиваем все сообщения (без лимита)
        processed_messages = 0
        text_count = 0
        voice_count = 0
        video_count = 0
        photo_count = 0
        
        async for message in client.iter_messages(chat_id):
            processed_messages += 1
            
            # Обновляем статус каждые 10 сообщений
            if processed_messages % 10 == 0:
                progress = min(90, int((processed_messages / total_messages) * 90))
                DOWNLOAD_STATUS[status_key].update({
                    "processed": processed_messages,
                    "progress": progress,
                    "text_count": text_count,
                    "voice_count": voice_count,
                    "video_count": video_count,
                    "photo_count": photo_count
                })
                print(f"⏳ Обработано сообщений: {processed_messages}/{total_messages}")
            
            # Скачиваем текстовые сообщения (всегда)
            if message.text:
                text_count += 1
                file_info = await download_media_file(client, message, media_path, "text")
                if file_info:
                    downloaded_files.append(file_info)
                    print(f"📝 Сохранено текстовое сообщение: {message.id}")
            
            # Скачиваем голосовые сообщения (если выбрано)
            if download_voice and (message.voice or (message.document and message.document.mime_type and 'audio' in message.document.mime_type)):
                voice_count += 1
                file_info = await download_media_file(client, message, media_path, "voice")
                if file_info:
                    downloaded_files.append(file_info)
                    # Подсчитываем размер файла
                    if os.path.exists(file_info['file_path']):
                        file_size = os.path.getsize(file_info['file_path'])
                        total_size_mb += file_size / (1024 * 1024)
                    print(f"🎤 Скачан голосовой файл: {message.id}")
            
            # Скачиваем видео сообщения (если выбрано)
            if download_video and (message.video or (message.document and message.document.mime_type and 'video' in message.document.mime_type)):
                video_count += 1
                file_info = await download_media_file(client, message, media_path, "video")
                if file_info:
                    downloaded_files.append(file_info)
                    # Подсчитываем размер файла
                    if os.path.exists(file_info['file_path']):
                        file_size = os.path.getsize(file_info['file_path'])
                        total_size_mb += file_size / (1024 * 1024)
                    print(f"🎥 Скачан видео файл: {message.id}")
            
            # Скачиваем фотографии (всегда)
            if message.photo:
                photo_count += 1
                file_info = await download_media_file(client, message, media_path, "photo")
                if file_info:
                    downloaded_files.append(file_info)
                    if os.path.exists(file_info['file_path']):
                        file_size = os.path.getsize(file_info['file_path'])
                        total_size_mb += file_size / (1024 * 1024)
                    print(f"🖼️ Скачана фотография: {message.id}")
        
        print(f"✅ Обработка завершена:")
        print(f"   • Текстовых: {text_count}")
        print(f"   • Голосовых: {voice_count}")
        print(f"   • Видео: {video_count}")
        print(f"   • Фото: {photo_count}")
        print(f"   • Общий размер: {round(total_size_mb, 2)} МБ")
        
        # Создаём отдельный файл с текстовыми сообщениями
        text_messages = []
        text_messages.append("=== ТЕКСТОВЫЕ СООБЩЕНИЯ ===\n")
        
        current_date = None
        for file_info in downloaded_files:
            if file_info['type'] == 'text':
                try:
                    with open(file_info['file_path'], 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Парсим информацию из файла
                    lines = content.split('\n')
                    message_id = None
                    date_str = None
                    text_content = ""
                    
                    for line in lines:
                        if line.startswith('ID: '):
                            message_id = line.replace('ID: ', '').strip()
                        elif line.startswith('Дата: '):
                            date_str = line.replace('Дата: ', '').strip()
                        elif line.startswith('Текст:'):
                            # Находим текст после "Текст:"
                            text_start = content.find('Текст:') + 6
                            text_end = content.find('-' * 50)
                            if text_end == -1:
                                text_end = len(content)
                            text_content = content[text_start:text_end].strip()
                            break
                    
                    if date_str and text_content:
                        # Парсим дату
                        try:
                            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            date_part = date_obj.strftime('%Y-%m-%d')
                            time_part = date_obj.strftime('%H:%M:%S')
                            
                            # Добавляем разделитель даты
                            if current_date != date_part:
                                current_date = date_part
                                text_messages.append(f"\n📅 {date_part}")
                            
                            text_messages.append(f"[{time_part}] Сообщение {message_id}: {text_content}")
                        except Exception as e:
                            print(f"❌ Ошибка парсинга даты {date_str}: {e}")
                            text_messages.append(f"[Неизвестное время] Сообщение {message_id}: {text_content}")
                    
                except Exception as e:
                    print(f"❌ Ошибка чтения текстового файла {file_info['file_path']}: {e}")
        
        text_messages.append("\n=== КОНЕЦ ТЕКСТОВЫХ СООБЩЕНИЙ ===")
        
        # Сохраняем текстовые сообщения в отдельный файл
        if text_messages:
            text_file = os.path.join(media_path, "text_messages.txt")
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(text_messages))
            print(f"📄 Создан файл с текстовыми сообщениями: {text_file}")
        
        # Сохраняем информацию о скачанных файлах
        info_file = os.path.join(media_path, "download_info.json")
        download_info = {
            "chat_id": chat_id,
            "chat_title": chat_title,
            "download_date": str(datetime.now()),
            "files": downloaded_files,
            "total_size_mb": round(total_size_mb, 2),
            "text_messages_count": len([f for f in downloaded_files if f['type'] == 'text']),
            "media_files_count": len([f for f in downloaded_files if f['type'] != 'text'])
        }
        
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(download_info, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Сохранена информация о скачивании: {info_file}")
        
        # Обновляем финальный статус
        DOWNLOAD_STATUS[status_key] = {
            "status": "completed",
            "processed": processed_messages,
            "total": total_messages,
            "progress": 100,
            "text_count": text_count,
            "voice_count": voice_count,
            "video_count": video_count,
            "total_size_mb": round(total_size_mb, 2)
        }
        
        result = {
            "status": "success",
            "chat_title": chat_title,
            "downloaded_count": len(downloaded_files),
            "total_messages": total_messages,
            "processed_messages": processed_messages,
            "media_path": media_path,
            "files": downloaded_files,
            "total_size_mb": round(total_size_mb, 2),
            "text_messages_count": len([f for f in downloaded_files if f['type'] == 'text']),
            "media_files_count": len([f for f in downloaded_files if f['type'] != 'text'])
        }
        
        print(f"🎉 Скачивание завершено успешно!")
        return result
        
    except Exception as e:
        print(f"❌ Ошибка скачивания: {e}")
        # Обновляем статус ошибки
        DOWNLOAD_STATUS[status_key] = {
            "status": "error",
            "error": str(e)
        }
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")
    finally:
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass

@app.get("/telegram/media/list")
async def list_downloaded_media():
    """Получить список скачанных медиафайлов"""
    if not os.path.exists(MEDIA_DOWNLOAD_DIR):
        return []
    
    media_list = []
    for chat_dir in os.listdir(MEDIA_DOWNLOAD_DIR):
        chat_path = os.path.join(MEDIA_DOWNLOAD_DIR, chat_dir)
        if os.path.isdir(chat_path):
            info_file = os.path.join(chat_path, "download_info.json")
            if os.path.exists(info_file):
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                    media_list.append(info)
                except Exception:
                    pass
    
    return media_list

def format_for_prompt(messages):
    """Форматирует сообщения для отправки в LLM"""
    if not messages:
        return "Переписка пуста."
    
    formatted = []
    formatted.append("=== ПЕРЕПИСКА ИЗ TELEGRAM ===\n")
    
    # Группируем сообщения по дате
    current_date = None
    for msg in messages:
        timestamp = msg['time'].replace('T', ' ').split('.')[0]
        date_part = timestamp.split(' ')[0]
        time_part = timestamp.split(' ')[1]
        sender = msg['from']
        
        # Добавляем разделитель даты
        if current_date != date_part:
            current_date = date_part
            formatted.append(f"\n📅 {date_part}")
        
        if msg['type'] == 'text':
            formatted.append(f"[{time_part}] {sender}: {msg['text']}")
        elif msg['type'] == 'voice':
            text = msg.get('text', '[аудиосообщение без расшифровки]')
            formatted.append(f"[{time_part}] {sender}: 🎤 {text}")
        elif msg['type'] == 'video':
            text = msg.get('text', '[видеосообщение]')
            formatted.append(f"[{time_part}] {sender}: 🎥 {text}")
        elif msg['type'] == 'photo':
            text = msg.get('text', '[фото]')
            formatted.append(f"[{time_part}] {sender}: 📷 {text}")
        elif msg['type'] == 'document':
            text = msg.get('text', '[документ]')
            formatted.append(f"[{time_part}] {sender}: 📄 {text}")
    
    formatted.append("\n=== КОНЕЦ ПЕРЕПИСКИ ===")
    return '\n'.join(formatted)

async def transcribe_audio(audio_path):
    """Расшифровывает аудиофайл с помощью Whisper"""
    try:
        # Проверяем, установлен ли faster-whisper
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            print("faster-whisper не установлен. Установите: pip install faster-whisper")
            return None
        
        # Загружаем модель Whisper
        model = WhisperModel("base", device="cpu", compute_type="int8")
        
        # Расшифровываем аудио
        segments, info = model.transcribe(audio_path, language="ru")
        
        # Собираем текст
        text = " ".join([segment.text for segment in segments])
        return text.strip()
        
    except Exception as e:
        print(f"Ошибка расшифровки аудио {audio_path}: {e}")
        return None

async def export_chat_for_llm(client, chat_id, limit=1000):
    """Экспортирует чат в формате для LLM"""
    try:
        # Инициализируем статус экспорта
        status_key = f"export_{chat_id}"
        EXPORT_STATUS[status_key] = {
            "status": "exporting",
            "processed": 0,
            "total": 0,
            "text_count": 0,
            "voice_count": 0,
            "video_count": 0,
            "photo_count": 0,
            "document_count": 0
        }
        
        # Получаем информацию о чате
        chat = await client.get_entity(chat_id)
        chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Unknown')
        
        # Создаём папки для экспорта
        safe_title = "".join(c for c in chat_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')
        export_dir = os.path.join(LLM_EXPORT_DIR, f"{chat_id}_{safe_title}")
        media_dir = os.path.join(export_dir, "media")
        os.makedirs(export_dir, exist_ok=True)
        os.makedirs(media_dir, exist_ok=True)
        
        messages = []
        processed_count = 0
        total_size_mb = 0
        downloaded_files = 0
        text_count = 0
        voice_count = 0
        video_count = 0
        photo_count = 0
        document_count = 0
        
        # Сначала подсчитаем общее количество сообщений
        total_messages = 0
        async for _ in client.iter_messages(chat_id, limit=limit):
            total_messages += 1
        
        # Обновляем статус
        EXPORT_STATUS[status_key]["total"] = total_messages
        
        # Получаем сообщения
        async for message in client.iter_messages(chat_id, limit=limit):
            processed_count += 1
            
            # Обновляем статус каждые 10 сообщений
            if processed_count % 10 == 0:
                EXPORT_STATUS[status_key].update({
                    "processed": processed_count,
                    "text_count": text_count,
                    "voice_count": voice_count,
                    "video_count": video_count,
                    "photo_count": photo_count,
                    "document_count": document_count
                })
            
            # Определяем отправителя
            if message.from_id:
                try:
                    sender = await client.get_entity(message.from_id)
                    sender_name = getattr(sender, 'first_name', None) or getattr(sender, 'username', None) or 'Unknown'
                except:
                    sender_name = 'Unknown'
            else:
                sender_name = 'me'
            
            # Форматируем время
            time_str = message.date.strftime("%Y-%m-%dT%H:%M:%S")
            
            msg_data = {
                "from": sender_name,
                "time": time_str,
                "message_id": message.id
            }
            
            # Обрабатываем разные типы сообщений
            if message.text:
                text_count += 1
                msg_data.update({
                    "type": "text",
                    "text": message.text
                })
                messages.append(msg_data)
                
            elif message.voice:
                # Скачиваем голосовое сообщение
                date_str = message.date.strftime("%Y-%m-%d_%H-%M-%S")
                voice_file = f"voice_{date_str}_{message.id}.ogg"
                voice_path = os.path.join(media_dir, voice_file)
                
                if not os.path.exists(voice_path):
                    await client.download_media(message.voice, voice_path)
                    # Подсчитываем размер файла
                    if os.path.exists(voice_path):
                        file_size = os.path.getsize(voice_path)
                        total_size_mb += file_size / (1024 * 1024)
                        downloaded_files += 1
                
                # Расшифровываем аудио
                transcription = await transcribe_audio(voice_path)
                
                voice_count += 1
                msg_data.update({
                    "type": "voice",
                    "file": voice_file,
                    "text": transcription or "[аудиосообщение без расшифровки]",
                    "duration": getattr(message.voice, 'duration', None)
                })
                messages.append(msg_data)
                
            elif message.video:
                # Скачиваем видео
                date_str = message.date.strftime("%Y-%m-%d_%H-%M-%S")
                video_file = f"video_{date_str}_{message.id}.mp4"
                video_path = os.path.join(media_dir, video_file)
                
                if not os.path.exists(video_path):
                    await client.download_media(message.video, video_path)
                    # Подсчитываем размер файла
                    if os.path.exists(video_path):
                        file_size = os.path.getsize(video_path)
                        total_size_mb += file_size / (1024 * 1024)
                        downloaded_files += 1
                
                video_count += 1
                msg_data.update({
                    "type": "video",
                    "file": video_file,
                    "text": getattr(message, 'caption', None) or "[видеосообщение]",
                    "duration": getattr(message.video, 'duration', None)
                })
                messages.append(msg_data)
                
            elif message.photo:
                photo_count += 1
                # Скачиваем фото
                date_str = message.date.strftime("%Y-%m-%d_%H-%M-%S")
                photo_file = f"photo_{date_str}_{message.id}.jpg"
                photo_path = os.path.join(media_dir, photo_file)
                
                if not os.path.exists(photo_path):
                    await client.download_media(message.photo, photo_path)
                    # Подсчитываем размер файла
                    if os.path.exists(photo_path):
                        file_size = os.path.getsize(photo_path)
                        total_size_mb += file_size / (1024 * 1024)
                        downloaded_files += 1
                
                msg_data.update({
                    "type": "photo",
                    "file": photo_file,
                    "text": getattr(message, 'caption', None) or "[фото]"
                })
                messages.append(msg_data)
                
            elif message.document:
                document_count += 1
                # Скачиваем документ
                date_str = message.date.strftime("%Y-%m-%d_%H-%M-%S")
                doc_name = getattr(message.document, 'attributes', [{}])[0].get('file_name', f'document_{message.id}')
                doc_file = f"doc_{date_str}_{message.id}_{doc_name}"
                doc_path = os.path.join(media_dir, doc_file)
                
                if not os.path.exists(doc_path):
                    await client.download_media(message.document, doc_path)
                    # Подсчитываем размер файла
                    if os.path.exists(doc_path):
                        file_size = os.path.getsize(doc_path)
                        total_size_mb += file_size / (1024 * 1024)
                        downloaded_files += 1
                
                msg_data.update({
                    "type": "document",
                    "file": doc_file,
                    "text": getattr(message, 'caption', None) or f"[документ: {doc_name}]"
                })
                messages.append(msg_data)
        
        # Сортируем сообщения по времени
        messages.sort(key=lambda x: x['time'])
        
        # Сохраняем в JSON
        json_file = os.path.join(export_dir, "chat_export.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        
        # Создаём текстовый файл для LLM с полной перепиской
        prompt_file = os.path.join(export_dir, "chat_for_llm.txt")
        formatted_text = format_for_prompt(messages)
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(formatted_text)
        
        # Создаём отдельный файл только с текстовыми сообщениями
        text_only_file = os.path.join(export_dir, "text_messages.txt")
        text_messages = []
        text_messages.append("=== ТЕКСТОВЫЕ СООБЩЕНИЯ ===\n")
        
        current_date = None
        for msg in messages:
            if msg['type'] == 'text':
                timestamp = msg['time'].replace('T', ' ').split('.')[0]
                date_part = timestamp.split(' ')[0]
                time_part = timestamp.split(' ')[1]
                sender = msg['from']
                
                # Добавляем разделитель даты
                if current_date != date_part:
                    current_date = date_part
                    text_messages.append(f"\n📅 {date_part}")
                
                text_messages.append(f"[{time_part}] {sender}: {msg['text']}")
        
        text_messages.append("\n=== КОНЕЦ ТЕКСТОВЫХ СООБЩЕНИЙ ===")
        
        with open(text_only_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(text_messages))
        
        # Обновляем финальный статус
        EXPORT_STATUS[status_key] = {
            "status": "completed",
            "processed": processed_count,
            "total": total_messages,
            "text_count": text_count,
            "voice_count": voice_count,
            "video_count": video_count,
            "photo_count": photo_count,
            "document_count": document_count
        }
        
        # Создаём метаданные
        metadata = {
            "chat_id": chat_id,
            "chat_title": chat_title,
            "export_date": str(datetime.now()),
            "total_messages": len(messages),
            "processed_messages": processed_count,
            "downloaded_files": downloaded_files,
            "total_size_mb": round(total_size_mb, 2),
            "media_count": len([m for m in messages if m['type'] != 'text']),
            "text_count": len([m for m in messages if m['type'] == 'text']),
            "voice_count": len([m for m in messages if m['type'] == 'voice']),
            "video_count": len([m for m in messages if m['type'] == 'video']),
            "photo_count": len([m for m in messages if m['type'] == 'photo']),
            "document_count": len([m for m in messages if m['type'] == 'document'])
        }
        
        meta_file = os.path.join(export_dir, "metadata.json")
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return {
            "status": "success",
            "chat_title": chat_title,
            "export_dir": export_dir,
            "metadata": metadata,
            "messages_count": len(messages),
            "downloaded_files": downloaded_files,
            "total_size_mb": round(total_size_mb, 2)
        }
        
    except Exception as e:
        print(f"Ошибка экспорта чата: {e}")
        # Обновляем статус ошибки
        EXPORT_STATUS[status_key] = {
            "status": "error",
            "error": str(e)
        }
        return {"status": "error", "detail": str(e)}

@app.post("/telegram/chat/{chat_id}/export-llm")
async def export_chat_llm(chat_id: int, data: TelegramDownloadRequest, limit: int = 1000):
    """Экспортирует чат в формате для LLM"""
    session_path = get_session_path(data.api_id, data.phone)
    client = None
    try:
        client = TelegramClient(session_path, data.api_id, data.api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            raise HTTPException(status_code=401, detail="Not authorized")
        
        result = await export_chat_for_llm(client, chat_id, limit)
        
        if result["status"] == "success":
            return result
        else:
            raise HTTPException(status_code=500, detail=result["detail"])
            
    except Exception as e:
        print(f"Ошибка экспорта: {e}")
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")
    finally:
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass

@app.get("/telegram/llm-exports")
async def list_llm_exports():
    """Получить список экспортов для LLM"""
    if not os.path.exists(LLM_EXPORT_DIR):
        return []
    
    exports = []
    for export_dir in os.listdir(LLM_EXPORT_DIR):
        export_path = os.path.join(LLM_EXPORT_DIR, export_dir)
        if os.path.isdir(export_path):
            meta_file = os.path.join(export_path, "metadata.json")
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    exports.append(metadata)
                except Exception:
                    pass
    
    return exports

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 