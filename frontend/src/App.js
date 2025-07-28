import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [config, setConfig] = useState({
    ai_model: 'gpt-3.5-turbo',
    telegram_api_key: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');

  // Загрузить конфигурацию при загрузке компонента
  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/config`);
      setConfig(response.data);
    } catch (error) {
      showMessage('Ошибка загрузки конфигурации', 'error');
      console.error('Error loading config:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API_BASE_URL}/config`, config);
      showMessage('Конфигурация успешно сохранена!', 'success');
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Ошибка сохранения конфигурации';
      showMessage(errorMessage, 'error');
      console.error('Error saving config:', error);
    } finally {
      setLoading(false);
    }
  };

  const showMessage = (text, type) => {
    setMessage(text);
    setMessageType(type);
    setTimeout(() => {
      setMessage('');
      setMessageType('');
    }, 3000);
  };

  const handleInputChange = (field, value) => {
    setConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const aiModels = [
    { value: 'gpt-3.5-turbo', label: 'GPT-3.5' },
    { value: 'gpt-4', label: 'GPT-4' },
    { value: 'gpt-4o', label: 'GPT-4o' },
    { value: 'llama3', label: 'Llama 3' }
  ];

  // --- Новое состояние для анализа ---
  const [analyzeTextValue, setAnalyzeTextValue] = useState('');
  const [analyzeResult, setAnalyzeResult] = useState('');
  const [analyzeLoading, setAnalyzeLoading] = useState(false);

  const analyzeText = async () => {
    if (!analyzeTextValue.trim()) {
      showMessage('Введите текст для анализа', 'error');
      return;
    }
    setAnalyzeLoading(true);
    setAnalyzeResult('');
    try {
      const response = await axios.post(`${API_BASE_URL}/api/analyze`, {
        text: analyzeTextValue,
        model: config.ai_model
      });
      setAnalyzeResult(response.data.result);
    } catch (error) {
      setAnalyzeResult('Ошибка анализа: ' + (error.response?.data?.detail || error.message));
    } finally {
      setAnalyzeLoading(false);
    }
  };

  // --- Telegram auth & download ---
  const [tgPhone, setTgPhone] = useState('');
  const [tgCode, setTgCode] = useState('');
  const [tgStep, setTgStep] = useState(1); // 1: phone, 2: code, 3: download
  const [tgUsername, setTgUsername] = useState('');
  const [tgChat, setTgChat] = useState('');
  const [tgLimit, setTgLimit] = useState(100);
  const [tgStatus, setTgStatus] = useState('');
  const [tgError, setTgError] = useState('');
  const [tgFile, setTgFile] = useState('');
  const [tgLoading, setTgLoading] = useState(false);

  const sendCode = async () => {
    setTgStatus(''); setTgError(''); setTgLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/auth/send_code`, { phone: tgPhone });
      setTgStatus('Код отправлен!');
      setTgStep(2);
    } catch (e) {
      setTgError(e.response?.data?.detail || 'Ошибка отправки кода');
    } finally { setTgLoading(false); }
  };

  const verifyCode = async () => {
    setTgStatus(''); setTgError(''); setTgLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/auth/verify_code`, { phone: tgPhone, code: tgCode });
      setTgStatus('Авторизация успешна! Ваш username: ' + res.data.username);
      setTgUsername(res.data.username);
      setTgStep(3);
    } catch (e) {
      setTgError(e.response?.data?.detail || 'Ошибка авторизации');
    } finally { setTgLoading(false); }
  };

  const downloadChat = async () => {
    setTgStatus(''); setTgError(''); setTgFile(''); setTgLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/download/chat`, {
        params: { username: tgUsername, chat: tgChat, limit: tgLimit }
      });
      setTgStatus('Переписка сохранена!');
      setTgFile(res.data.file);
    } catch (e) {
      setTgError(e.response?.data?.detail || 'Ошибка скачивания');
    } finally { setTgLoading(false); }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <h1 className="text-2xl font-bold text-gray-900">AI Bot</h1>
            <button
              onClick={saveConfig}
              disabled={loading}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Сохранение...' : 'Save'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Message */}
        {message && (
          <div className={`mb-6 p-4 rounded-lg ${
            messageType === 'success' 
              ? 'bg-green-100 text-green-800 border border-green-200' 
              : 'bg-red-100 text-red-800 border border-red-200'
          }`}>
            {message}
          </div>
        )}

        <div className="space-y-6">
          {/* AI Model Selection */}
          <div className="card animate-fade-in">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">AI Model</h2>
            <div className="space-y-2">
              <select
                value={config.ai_model}
                onChange={(e) => handleInputChange('ai_model', e.target.value)}
                className="input-field"
                disabled={loading}
              >
                {aiModels.map(model => (
                  <option key={model.value} value={model.value}>
                    {model.label}
                  </option>
                ))}
              </select>
              <p className="text-sm text-gray-500">Select model</p>
            </div>
          </div>

          {/* Telegram Settings */}
          <div className="card animate-fade-in">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Telegram Settings</h2>
            <div className="space-y-2">
              <input
                type="password"
                value={config.telegram_api_key}
                onChange={(e) => handleInputChange('telegram_api_key', e.target.value)}
                placeholder="Enter your Telegram API key"
                className="input-field"
                disabled={loading}
              />
              <p className="text-sm text-gray-500">
                Введите ваш Telegram Bot API ключ для интеграции
              </p>
            </div>
          </div>

          {/* Анализ текста (Telegram/любой) */}
          <div className="card animate-fade-in">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Анализировать переписку</h2>
            <textarea
              className="input-field w-full min-h-[120px] mb-2"
              placeholder="Вставьте переписку для анализа (например, из Telegram)"
              value={analyzeTextValue}
              onChange={e => setAnalyzeTextValue(e.target.value)}
              disabled={analyzeLoading}
            />
            <button
              className="btn-primary mt-2"
              onClick={analyzeText}
              disabled={analyzeLoading || !analyzeTextValue.trim()}
            >
              {analyzeLoading ? 'Анализ...' : 'Анализировать'}
            </button>
            {analyzeResult && (
              <div className="mt-4 p-3 bg-gray-100 rounded text-sm whitespace-pre-line">
                {analyzeResult}
              </div>
            )}
          </div>

          {/* --- Telegram: авторизация и скачивание чатов --- */}
          <div className="card animate-fade-in">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Telegram: авторизация и скачивание чатов</h2>
            {tgStep === 1 && (
              <>
                <input
                  className="input-field w-full mb-2"
                  placeholder="Телефон (например, +79998887766)"
                  value={tgPhone}
                  onChange={e => setTgPhone(e.target.value)}
                  disabled={tgLoading}
                />
                <button
                  className="btn-primary"
                  onClick={sendCode}
                  disabled={tgLoading || !tgPhone.trim()}
                >
                  {tgLoading ? 'Отправка...' : 'Получить код'}
                </button>
              </>
            )}
            {tgStep === 2 && (
              <>
                <input
                  className="input-field w-full mb-2"
                  placeholder="Код из Telegram"
                  value={tgCode}
                  onChange={e => setTgCode(e.target.value)}
                  disabled={tgLoading}
                />
                <button
                  className="btn-primary"
                  onClick={verifyCode}
                  disabled={tgLoading || !tgCode.trim()}
                >
                  {tgLoading ? 'Проверка...' : 'Войти'}
                </button>
              </>
            )}
            {tgStep === 3 && (
              <>
                <input
                  className="input-field w-full mb-2"
                  placeholder="Ваш Telegram username (авто)"
                  value={tgUsername}
                  onChange={e => setTgUsername(e.target.value)}
                  disabled
                />
                <input
                  className="input-field w-full mb-2"
                  placeholder="Чат/канал (например, @somechannel)"
                  value={tgChat}
                  onChange={e => setTgChat(e.target.value)}
                  disabled={tgLoading}
                />
                <input
                  className="input-field w-full mb-2"
                  type="number"
                  min={1}
                  max={10000}
                  placeholder="Сколько сообщений (limit)"
                  value={tgLimit}
                  onChange={e => setTgLimit(Number(e.target.value))}
                  disabled={tgLoading}
                />
                <button
                  className="btn-primary"
                  onClick={downloadChat}
                  disabled={tgLoading || !tgChat.trim()}
                >
                  {tgLoading ? 'Скачивание...' : 'Скачать переписку'}
                </button>
              </>
            )}
            {(tgStatus || tgError || tgFile) && (
              <div className="mt-3">
                {tgStatus && <div className="text-green-700 mb-1">{tgStatus}</div>}
                {tgError && <div className="text-red-700 mb-1">{tgError}</div>}
                {tgFile && <div className="text-xs text-gray-500">Файл: {tgFile}</div>}
              </div>
            )}
          </div>

          {/* Future Features Preview */}
          <div className="card animate-fade-in">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Будущие функции</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="font-medium text-gray-900 mb-2">📁 Загрузка переписок</h3>
                <p className="text-sm text-gray-600">
                  Поддержка JSON и .txt файлов
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="font-medium text-gray-900 mb-2">🧠 NLP анализ</h3>
                <p className="text-sm text-gray-600">
                  Токенизация, sentiment, резюме
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="font-medium text-gray-900 mb-2">📱 Telegram API</h3>
                <p className="text-sm text-gray-600">
                  Получение и анализ чатов
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-16 bg-white border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-sm text-gray-500">
            AI Bot Manager v1.0.0
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App; 