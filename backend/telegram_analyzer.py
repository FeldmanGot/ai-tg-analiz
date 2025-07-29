#!/usr/bin/env python3
"""
Комбинированная система анализа переписок с Telegram
"""

import os
import json
import asyncio
import whisper
from datetime import datetime
from typing import List, Dict, Optional
from telethon import TelegramClient, events
from telethon.tl.types import Message, MessageMediaDocument, MessageMediaPhoto
from telethon.errors import SessionPasswordNeededError
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramAnalyzer:
    def __init__(self, api_id: int, api_hash: str, phone: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.client = None
        
        # Создаём структуру папок
        self.data_dir = "data"
        self.sessions_dir = os.path.join(self.data_dir, "sessions")
        self.live_dir = os.path.join(self.data_dir, "live")
        self.media_dir = os.path.join(self.data_dir, "media")
        self.profiles_dir = os.path.join(self.data_dir, "profiles")
        
        for directory in [self.sessions_dir, self.live_dir, self.media_dir, self.profiles_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Инициализируем Whisper
        try:
            self.whisper_model = whisper.load_model("base")
            logger.info("✅ Whisper модель загружена")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки Whisper: {e}")
            self.whisper_model = None
    
    async def connect(self):
        """Подключаемся к Telegram"""
        session_path = os.path.join(self.sessions_dir, f"{self.phone}.session")
        self.client = TelegramClient(session_path, self.api_id, self.api_hash)
        
        try:
            await self.client.connect()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {e}")
            return False
    
    async def check_auth(self):
        """Проверяет авторизацию"""
        if not self.client or not self.client.is_connected():
            return False
        return await self.client.is_user_authorized()
    
    async def send_code(self):
        """Отправляет код подтверждения"""
        try:
            self.phone_code_hash = await self.client.send_code_request(self.phone)
            logger.info(f"✅ Код отправлен на {self.phone}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка отправки кода: {e}")
            return False
    
    async def sign_in(self, code: str, password: str = None):
        """Входит с кодом подтверждения и паролем если нужно"""
        try:
            # Пробуем войти с кодом
            await self.client.sign_in(self.phone, code, phone_code_hash=self.phone_code_hash.phone_code_hash)
            logger.info("✅ Авторизация успешна")
            return {"status": "success"}
        except SessionPasswordNeededError:
            # Требуется пароль
            if password:
                try:
                    await self.client.sign_in(password=password)
                    logger.info("✅ Авторизация с паролем успешна")
                    return {"status": "success"}
                except Exception as e:
                    logger.error(f"❌ Ошибка входа с паролем: {e}")
                    return {"status": "error", "message": str(e)}
            else:
                logger.info("⚠️ Требуется пароль для 2FA")
                return {"status": "2fa_required"}
        except Exception as e:
            logger.error(f"❌ Ошибка входа: {e}")
            return {"status": "error", "message": str(e)}
    
    async def disconnect(self):
        """Отключаемся от Telegram"""
        if self.client:
            await self.client.disconnect()
            logger.info("🔌 Отключено от Telegram")
    
    def get_chat_key(self, chat) -> str:
        """Получаем ключ чата для файлов"""
        if hasattr(chat, 'username') and chat.username:
            return f"@{chat.username}"
        elif hasattr(chat, 'title'):
            return chat.title.replace(' ', '_').replace('/', '_')
        else:
            return str(chat.id)
    
    async def download_history(self, chat: str, limit: int = 3000) -> bool:
        """Скачивает всю историю сообщений"""
        try:
            # Получаем чат
            if chat.startswith('@'):
                entity = await self.client.get_entity(chat)
            else:
                entity = await self.client.get_entity(int(chat))
            
            chat_key = self.get_chat_key(entity)
            logger.info(f"📥 Скачиваем историю для {chat_key} (лимит: {limit})")
            
            # Файлы для сохранения
            live_file = os.path.join(self.live_dir, f"{chat_key}.json")
            profile_file = os.path.join(self.profiles_dir, f"{chat_key}_profile.json")
            
            messages = []
            processed = 0
            
            # Скачиваем сообщения
            async for message in self.client.iter_messages(entity, limit=limit):
                processed += 1
                if processed % 100 == 0:
                    logger.info(f"⏳ Обработано сообщений: {processed}")
                
                msg_data = await self.process_message(message)
                if msg_data:
                    messages.append(msg_data)
            
            # Сохраняем в JSON
            with open(live_file, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ История сохранена: {len(messages)} сообщений")
            
            # Создаём начальный профиль
            if messages:
                await self.create_initial_profile(chat_key, messages)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания истории: {e}")
            return False
    
    async def process_message(self, message: Message) -> Optional[Dict]:
        """Обрабатывает одно сообщение"""
        try:
            # Определяем отправителя
            if message.from_id:
                try:
                    sender = await self.client.get_entity(message.from_id)
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
                msg_data.update({
                    "type": "text",
                    "text": message.text
                })
                return msg_data
                
            elif message.voice:
                # Скачиваем голосовое сообщение
                voice_file = await self.download_media(message.voice, "voice")
                if voice_file:
                    # Расшифровываем аудио
                    transcription = await self.whisper_transcribe(voice_file)
                    msg_data.update({
                        "type": "voice",
                        "text": f"[аудио: {transcription}]" if transcription else "[аудио: не удалось расшифровать]",
                        "file": os.path.basename(voice_file)
                    })
                    return msg_data
                    
            elif message.video:
                # Скачиваем видео
                video_file = await self.download_media(message.video, "video")
                if video_file:
                    msg_data.update({
                        "type": "video",
                        "text": "[видео]",
                        "file": os.path.basename(video_file)
                    })
                    return msg_data
                    
            elif message.photo:
                # Скачиваем фото
                photo_file = await self.download_media(message.photo, "photo")
                if photo_file:
                    msg_data.update({
                        "type": "photo",
                        "text": "[фото]",
                        "file": os.path.basename(photo_file)
                    })
                    return msg_data
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения {message.id}: {e}")
            return None
    
    async def download_media(self, media, media_type: str) -> Optional[str]:
        """Скачивает медиафайл"""
        try:
            date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{media_type}_{date_str}_{media.id}"
            
            if media_type == "voice":
                filename += ".ogg"
            elif media_type == "video":
                filename += ".mp4"
            elif media_type == "photo":
                filename += ".jpg"
            
            file_path = os.path.join(self.media_dir, filename)
            
            if not os.path.exists(file_path):
                await self.client.download_media(media, file_path)
                logger.info(f"📁 Скачан файл: {filename}")
            
            return file_path
            
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания медиа: {e}")
            return None
    
    async def whisper_transcribe(self, file_path: str) -> Optional[str]:
        """Расшифровывает аудио через Whisper"""
        if not self.whisper_model:
            return None
        
        try:
            result = self.whisper_model.transcribe(file_path, language="ru")
            return result["text"].strip()
        except Exception as e:
            logger.error(f"❌ Ошибка расшифровки аудио: {e}")
            return None
    
    async def create_initial_profile(self, chat_key: str, messages: List[Dict]):
        """Создаёт начальный профиль на основе истории"""
        try:
            # Анализируем последние 100 сообщений для создания профиля
            recent_messages = messages[-100:] if len(messages) > 100 else messages
            
            # Форматируем для анализа
            formatted_messages = self.format_for_prompt(recent_messages)
            
            # Анализируем через LLM
            analysis = await self.analyze_with_context(formatted_messages, {})
            
            # Создаём профиль
            profile = {
                "chat_key": chat_key,
                "created_at": datetime.now().isoformat(),
                "total_messages": len(messages),
                "analysis": analysis,
                "last_updated": datetime.now().isoformat()
            }
            
            # Сохраняем профиль
            profile_file = os.path.join(self.profiles_dir, f"{chat_key}_profile.json")
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
            
            # Сохраняем последний анализ
            analysis_file = os.path.join(self.profiles_dir, f"{chat_key}_last_analysis.txt")
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write(analysis)
            
            logger.info(f"✅ Создан профиль для {chat_key}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания профиля: {e}")
    
    def format_for_prompt(self, messages: List[Dict], profile: Dict = None) -> str:
        """Форматирует сообщения для LLM"""
        formatted = []
        
        for msg in messages:
            time_str = msg['time'].replace('T', ' ')
            sender = msg['from']
            text = msg['text']
            formatted.append(f"[{time_str}] {sender}: {text}")
        
        result = "\n".join(formatted)
        
        if profile and profile.get('analysis'):
            result += f"\n\n📝 Профиль:\n{profile['analysis']}"
        
        return result
    
    async def analyze_with_context(self, messages_text: str, profile: Dict) -> str:
        """Анализирует сообщения с контекстом профиля"""
        try:
            # Здесь будет вызов LLM
            # Пока возвращаем заглушку
            prompt = f"""
Анализируй переписку и обновляй профиль пользователя.

Переписка:
{messages_text}

Проанализируй:
1. Тему общения
2. Тональность (дружелюбная, формальная, эмоциональная)
3. Стиль общения (лаконичный, подробный, с эмодзи)
4. Намерения участников
5. Динамику отношений

Ответь в формате:
Тема: [тема]
Тон: [тональность] 
Стиль: [стиль общения]
Намерения: [что хотят участники]
Динамика: [как развиваются отношения]
            """
            
            # TODO: Заменить на реальный вызов LLM
            return "Анализ будет выполнен через LLM"
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа: {e}")
            return "Ошибка анализа"
    
    async def listen_to_new_messages(self, chat: str):
        """Слушает новые сообщения в реальном времени"""
        try:
            # Получаем чат
            if chat.startswith('@'):
                entity = await self.client.get_entity(chat)
            else:
                entity = await self.client.get_entity(int(chat))
            
            chat_key = self.get_chat_key(entity)
            logger.info(f"👂 Слушаем новые сообщения в {chat_key}")
            
            @self.client.on(events.NewMessage(chats=entity))
            async def handle_new_message(event):
                try:
                    # Обрабатываем новое сообщение
                    msg_data = await self.process_message(event.message)
                    if msg_data:
                        # Добавляем в live файл
                        await self.add_to_live(chat_key, msg_data)
                        
                        # Анализируем с контекстом
                        await self.analyze_new_message(chat_key, msg_data)
                        
                        logger.info(f"📨 Новое сообщение от {msg_data['from']}: {msg_data['text'][:50]}...")
                
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки нового сообщения: {e}")
            
            # Запускаем слушание
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска слушания: {e}")
    
    async def add_to_live(self, chat_key: str, msg_data: Dict):
        """Добавляет новое сообщение в live файл"""
        try:
            live_file = os.path.join(self.live_dir, f"{chat_key}.json")
            
            # Загружаем существующие сообщения
            messages = []
            if os.path.exists(live_file):
                with open(live_file, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
            
            # Добавляем новое сообщение
            messages.append(msg_data)
            
            # Сохраняем обратно
            with open(live_file, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Ошибка добавления в live: {e}")
    
    async def analyze_new_message(self, chat_key: str, new_msg: Dict):
        """Анализирует новое сообщение с контекстом"""
        try:
            # Загружаем профиль
            profile_file = os.path.join(self.profiles_dir, f"{chat_key}_profile.json")
            profile = {}
            if os.path.exists(profile_file):
                with open(profile_file, 'r', encoding='utf-8') as f:
                    profile = json.load(f)
            
            # Загружаем последние 30 сообщений
            live_file = os.path.join(self.live_dir, f"{chat_key}.json")
            recent_messages = []
            if os.path.exists(live_file):
                with open(live_file, 'r', encoding='utf-8') as f:
                    all_messages = json.load(f)
                    recent_messages = all_messages[-30:]  # Последние 30
            
            # Форматируем для анализа
            formatted_messages = self.format_for_prompt(recent_messages, profile)
            
            # Анализируем
            new_analysis = await self.analyze_with_context(formatted_messages, profile)
            
            # Обновляем профиль
            profile['last_updated'] = datetime.now().isoformat()
            profile['analysis'] = new_analysis
            
            # Сохраняем обновлённый профиль
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
            
            # Сохраняем последний анализ
            analysis_file = os.path.join(self.profiles_dir, f"{chat_key}_last_analysis.txt")
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write(new_analysis)
            
            logger.info(f"✅ Профиль {chat_key} обновлён")
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа нового сообщения: {e}")

# Пример использования
async def main():
    """Пример использования системы"""
    analyzer = TelegramAnalyzer(
        api_id=YOUR_API_ID,
        api_hash="YOUR_API_HASH",
        phone="YOUR_PHONE"
    )
    
    # Подключаемся
    if await analyzer.connect():
        # Скачиваем историю
        await analyzer.download_history("@azalia", limit=3000)
        
        # Слушаем новые сообщения
        await analyzer.listen_to_new_messages("@azalia")
    
    await analyzer.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 