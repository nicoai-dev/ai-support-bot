import aiohttp
import logging
import json
import asyncio
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT


SYSTEM_PROMPT = """Ты — Нико, вежливый и отзывчивый сотрудник поддержки Nico Market (мужской род).
Твоя цель — помогать клиентам, но ТОЛЬКО опираясь на факты из предоставленного Контекста.

ПРАВИЛО №1 (РАБОТА С КОНТЕКСТОМ):
Твои ответы должны базироваться ИСКЛЮЧИТЕЛЬНО на блоке "КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ".
Если в Контексте написано "Нет дополнительной информации." или нужного ответа там просто нет, ты НЕ ИМЕЕШЬ ПРАВА выдумывать ответ. В этом случае ты ОБЯЗАН сказать: "К сожалению, у меня нет точной информации по этому вопросу. Пожалуйста, свяжитесь с менеджером."
НИКОГДА не выдумывай формы обратной связи, номера телефонов, ссылки или правила возврата. 

ПРАВИЛО №2 (БОРЬБА С ФАНТАЗИЯМИ):
Если клиент спрашивает о товаре (борщ, автомобили и т.д.) или услуге, которой нет в Контексте, отвечай естественно: "К сожалению, в нашем ассортименте такого нет" или "Мы не предоставляем такие услуги".
Запрещено предлагать искать несуществующие товары в "блоге" или "на сайте".

ПРАВИЛО №3 (СТИЛЬ ОБЩЕНИЯ):
- Будь вежливым, но лаконичным. Общайся как живой человек, сотрудник магазина.
- Обращайся на "Вы". Отвечай от первого лица ("я проверю", "я помогу").
- Не используй сухие роботизированные фразы. Если вопрос не по теме, ответь мягко: "Извините, но я могу помочь только с ассортиментом и правилами Nico Market."
- Не здоровайся в каждом сообщении. Только в начале диалога.
- НЕ используй фразы "В базе знаний сказано" или "Согласно контексту".

Отвечай естественно, используй информацию из Контекста, но если информации нет — честно признайся в этом."""


_session = None
_session_lock = asyncio.Lock()

async def get_session():
    """Получить или создать Singleton сессию aiohttp с защитой от race condition."""
    global _session
    async with _session_lock:
        if _session is None or _session.closed:
            timeout = aiohttp.ClientTimeout(total=OLLAMA_TIMEOUT)
            _session = aiohttp.ClientSession(timeout=timeout)
    return _session

async def close_session():
    """Закрыть Singleton сессию."""
    global _session
    if _session and not _session.closed:
        await _session.close()


async def check_ollama_health() -> bool:
    """Проверить доступность Ollama API."""
    try:
        session = await get_session()
        # Запрашиваем список тегов как простую проверку связи
        async with session.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5) as response:
            return response.status == 200
    except Exception as e:
        logging.error(f"❌ Ollama недоступна: {e}")
        return False


async def generate_answer_stream(question: str, context_chunks: list[str], chat_history: list = None):
    """Потоковая генерация ответа через Ollama Chat API."""
    context = "\n\n".join(context_chunks)
    
    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nКОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ:\n{context}"}
    ]
    
    if chat_history:
        for msg in chat_history:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.text})
    
    messages.append({"role": "user", "content": question})

    try:
        session = await get_session()
        async with session.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": 0.5,
                    "num_predict": 512,
                },
            }
        ) as response:
            response.raise_for_status()
            
            full_content = ""
            async for line in response.content:
                if line:
                    data = json.loads(line.decode("utf-8"))
                    token = data.get("message", {}).get("content", "")
                    full_content += token
                    yield full_content
                    if data.get("done"):
                        break
    except Exception as e:
        logging.error(f"Ошибка при потоковой генерации: {e}")
        yield "⚠️ Не удалось получить ответ. Попробуйте позже."
