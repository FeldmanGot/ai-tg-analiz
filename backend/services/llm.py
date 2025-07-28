import httpx

PROMPT_TEMPLATE = '''Ты — аналитик общения и психолог.
Проанализируй следующую переписку между пользователями. Выдели:
1. Характеристика каждого участника (темперамент, стиль, эмоции, роль)
2. Характер взаимоотношений (близость, доминирование, признаки симпатии, конфликт)
3. Общие черты общения (темы, словарь, темп)
4. Итоговая выдержка (по каждому участнику и общая картина)

💬 Вот переписка:
{text}

💡 Подскажи пользователю структуру ответа: по пунктам или в JSON-формате.
'''

def build_prompt(text: str) -> str:
    return PROMPT_TEMPLATE.format(text=text)

async def analyze_with_ollama(prompt: str, model: str) -> str:
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data.get("response") or data.get("result") or str(data)

async def analyze_text(text: str, model: str) -> str:
    prompt = build_prompt(text)
    return await analyze_with_ollama(prompt, model)

# --- Заглушка для получения сообщений из Telegram ---
def get_messages():
    """
    Получить сообщения из Telegram (заглушка).
    В будущем реализовать через Telegram Bot API.
    """
    # Пример возврата переписки
    return [
        {"user": "User1", "text": "Привет! Как дела?"},
        {"user": "User2", "text": "Все хорошо, спасибо! А у тебя?"},
        {"user": "User1", "text": "Тоже отлично!"}
    ] 