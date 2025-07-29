#!/usr/bin/env python3
"""
Тестовый скрипт для проверки новой системы авторизации
"""

import asyncio
import sys
sys.path.append('backend')

from telegram_analyzer import TelegramAnalyzer

async def test_auth():
    """Тестирование авторизации"""
    
    # Тестовые данные (замените на свои)
    api_id = 12345  # Ваш API ID
    api_hash = "your_api_hash"  # Ваш API Hash
    phone = "+7XXXXXXXXXX"  # Ваш телефон
    
    print("🚀 Тестирование новой системы авторизации")
    print("-" * 50)
    
    # Создаём анализатор
    analyzer = TelegramAnalyzer(api_id, api_hash, phone)
    
    # Подключаемся
    print("📱 Подключение к Telegram...")
    if await analyzer.connect():
        print("✅ Подключение установлено")
        
        # Проверяем авторизацию
        if await analyzer.check_auth():
            print("✅ Уже авторизован!")
        else:
            print("❌ Не авторизован, отправляем код...")
            
            # Отправляем код
            if await analyzer.send_code():
                print("✅ Код отправлен на телефон")
                
                # Ждём ввода кода
                code = input("📱 Введите код из Telegram: ")
                
                # Пробуем войти
                result = await analyzer.sign_in(code)
                
                if result["status"] == "success":
                    print("✅ Авторизация успешна!")
                elif result["status"] == "2fa_required":
                    print("🔐 Требуется пароль для 2FA")
                    password = input("🔑 Введите пароль: ")
                    
                    # Пробуем с паролем
                    result = await analyzer.sign_in(code, password)
                    
                    if result["status"] == "success":
                        print("✅ Авторизация с паролем успешна!")
                    else:
                        print(f"❌ Ошибка: {result.get('message', 'Неизвестная ошибка')}")
                else:
                    print(f"❌ Ошибка: {result.get('message', 'Неизвестная ошибка')}")
            else:
                print("❌ Не удалось отправить код")
    else:
        print("❌ Не удалось подключиться")
    
    # Отключаемся
    await analyzer.disconnect()
    print("\n✅ Тест завершён")

if __name__ == "__main__":
    asyncio.run(test_auth()) 