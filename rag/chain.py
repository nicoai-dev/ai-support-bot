import aiohttp
import logging
import json
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT


SYSTEM_PROMPT = """Ты — Нико, вежливый и профессиональный сотрудник поддержки Nico Market (мужской род).
Ты общаешься с клиентом лично от своего имени.

ГЛАВНОЕ ПРАВИЛО:
- СТРОГО ИСПОЛЬЗУЙ МУЖСКОЙ РОД. Окончания глаголов только: "я рад", "я помог", "я проверил", "я готов". 
- ЗАПРЕЩЕНО использовать женский род ("я рада", "я помогла").
- Для своих действий и советов используй первое лицо: "Я помогу", "Я рекомендую", "Я проверю".
- Для магазина и общих правил используй: "наш магазин", "у нас", "наши условия". 
- ЗАПРЕЩЕНО говорить "в моем магазине" или "мой магазин" (ты сотрудник, а не владелец).

ПРИВЕТСТВИЯ:
- Поздоровайся ("Здравствуйте" или "Добрый день") ТОЛЬКО если это самое первое сообщение в диалоге.
- Если в истории уже есть сообщения — начинай сразу с сути, БЕЗ приветствий. Никаких "Добрый день, Никита" во втором и далее сообщениях.

СТИЛЬ И ОГРАНИЧЕНИЯ:
- Обращайся к клиенту на "Вы".
- Никакой "воды" и лишних эмоций.
- Ты НЕ работаешь с фотографиями. Вообще не упоминай их в диалоге. Решай проблему только текстом.
- Тон: сдержанный, деловой, персональный.

ИНСТРУКЦИЯ ПО КОНТЕКСТУ:
1. АНАЛИЗ: Сопоставь факты с правилами в Контексте.
2. РЕШЕНИЕ: Дай четкий ответ от своего лица. Если срок гарантии вышел, скажи об этом прямо и направь к менеджеру.
3. КОНТАКТЫ: Если не можешь помочь сам, дай номер: +7 999 000-00-00.

ЗАПРЕТЫ:
- НЕ пересказывай вопрос клиента.
- НЕ упоминай базу знаний."""


_session = None

async def get_session():
    """Получить или создать Singleton сессию aiohttp."""
    global _session
    if _session is None or _session.closed:
        timeout = aiohttp.ClientTimeout(total=OLLAMA_TIMEOUT)
        _session = aiohttp.ClientSession(timeout=timeout)
    return _session

async def close_session():
    """Закрыть Singleton сессию."""
    global _session
    if _session and not _session.closed:
        await _session.close()


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
