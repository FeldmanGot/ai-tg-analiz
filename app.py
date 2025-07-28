#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import webbrowser
import threading
import time

app = Flask(__name__)

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

def save_config(config):
    """Сохранить конфигурацию в файл"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

# HTML шаблон с современным дизайном
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Bot Manager</title>
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
                <h1 class="text-2xl font-bold text-gray-900">AI Bot</h1>
                <button onclick="saveConfig()" class="btn-primary" id="saveBtn">
                    Save
                </button>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- Message -->
        <div id="message" class="hidden mb-6 p-4 rounded-lg"></div>

        <div class="space-y-6">
            <!-- AI Model Selection -->
            <div class="card animate-fade-in">
                <h2 class="text-xl font-semibold text-gray-900 mb-4">AI Model</h2>
                <div class="space-y-2">
                    <select id="aiModel" class="input-field">
                        <option value="gpt-3.5-turbo">GPT-3.5</option>
                        <option value="gpt-4">GPT-4</option>
                        <option value="gpt-4o">GPT-4o</option>
                    </select>
                    <p class="text-sm text-gray-500">Select model</p>
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
                        Введите ваш Telegram Bot API ключ для интеграции
                    </p>
                </div>
            </div>

            <!-- Future Features Preview -->
            <div class="card animate-fade-in">
                <h2 class="text-xl font-semibold text-gray-900 mb-4">Будущие функции</h2>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="p-4 bg-gray-50 rounded-lg">
                        <h3 class="font-medium text-gray-900 mb-2">📁 Загрузка переписок</h3>
                        <p class="text-sm text-gray-600">
                            Поддержка JSON и .txt файлов
                        </p>
                    </div>
                    <div class="p-4 bg-gray-50 rounded-lg">
                        <h3 class="font-medium text-gray-900 mb-2">🧠 NLP анализ</h3>
                        <p class="text-sm text-gray-600">
                            Токенизация, sentiment, резюме
                        </p>
                    </div>
                    <div class="p-4 bg-gray-50 rounded-lg">
                        <h3 class="font-medium text-gray-900 mb-2">📱 Telegram API</h3>
                        <p class="text-sm text-gray-600">
                            Получение и анализ чатов
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="mt-16 bg-white border-t border-gray-200">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <p class="text-center text-sm text-gray-500">
                AI Bot Manager v1.0.0
            </p>
        </div>
    </footer>

    <script>
        // Загрузить конфигурацию при загрузке страницы
        window.addEventListener('load', function() {
            loadConfig();
        });

        async function loadConfig() {
            try {
                const response = await fetch('/api/config');
                const config = await response.json();
                
                document.getElementById('aiModel').value = config.ai_model;
                document.getElementById('telegramApiKey').value = config.telegram_api_key;
            } catch (error) {
                console.error('Error loading config:', error);
            }
        }

        async function saveConfig() {
            const saveBtn = document.getElementById('saveBtn');
            const messageDiv = document.getElementById('message');
            
            // Показать состояние загрузки
            saveBtn.textContent = 'Сохранение...';
            saveBtn.disabled = true;
            
            try {
                const config = {
                    ai_model: document.getElementById('aiModel').value,
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

@app.route('/')
def index():
    """Главная страница"""
    return HTML_TEMPLATE

@app.route('/api/config', methods=['GET'])
def get_config():
    """Получить конфигурацию"""
    try:
        config = load_config()
        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config', methods=['POST'])
def save_config_api():
    """Сохранить конфигурацию"""
    try:
        data = request.get_json()
        
        # Валидация
        valid_models = ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]
        if data.get('ai_model') not in valid_models:
            return jsonify({"detail": "Неверная модель ИИ"}), 400
        
        if not data.get('telegram_api_key', '').strip():
            return jsonify({"detail": "Telegram API ключ не может быть пустым"}), 400
        
        save_config(data)
        return jsonify({"message": "Конфигурация успешно сохранена", "config": data})
    except Exception as e:
        return jsonify({"detail": f"Ошибка сохранения конфигурации: {str(e)}"}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_conversation():
    """Анализ переписки (заглушка)"""
    try:
        data = request.get_json()
        conversation = data.get('conversation', '')
        
        return jsonify({
            "message": "Анализ переписки",
            "conversation_length": len(conversation),
            "status": "pending_implementation"
        })
    except Exception as e:
        return jsonify({"detail": f"Ошибка анализа: {str(e)}"}), 500

def open_browser():
    """Открыть браузер через 1 секунду"""
    time.sleep(1)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    print("🚀 Запуск AI Bot Manager...")
    print("📱 Открытие браузера...")
    
    # Запустить браузер в отдельном потоке
    threading.Thread(target=open_browser, daemon=True).start()
    
    print("🌐 Приложение доступно по адресу: http://localhost:5000")
    print("📋 Функции:")
    print("   - Выбор модели ИИ (GPT-3.5, GPT-4, GPT-4o)")
    print("   - Настройка Telegram API ключа")
    print("   - Сохранение конфигурации")
    print("   - Современный адаптивный дизайн")
    print("\n💡 Для остановки нажмите Ctrl+C")
    
    # Запустить Flask приложение
    app.run(debug=False, host='0.0.0.0', port=5000) 