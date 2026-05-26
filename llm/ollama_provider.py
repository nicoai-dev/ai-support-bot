import aiohttp
import asyncio
import json
import logging
from typing import AsyncIterator
from llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """LLM-провайдер для Ollama (локальная модель)."""
    
    def __init__(self, base_url: str, model: str, timeout: int = 300, context_window: int = 16384):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.context_window = context_window
        self._session: aiohttp.ClientSession | None = None
        self._session_lock = asyncio.Lock()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать singleton HTTP-сессию."""
        async with self._session_lock:
            if self._session is None or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def chat_stream(
        self, 
        messages: list[dict], 
        temperature: float = 0.5, 
        max_tokens: int = 768,
    ) -> AsyncIterator[str]:
        """Потоковая генерация через Ollama /api/chat."""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "repeat_penalty": 1.1,
                        "top_p": 0.9,
                        "num_ctx": self.context_window,
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
            logging.error(f"Ошибка при потоковой генерации Ollama: {e}")
            yield "⚠️ Не удалось получить ответ. Пожалуйста, повторите запрос через несколько секунд."
    
    async def chat(
        self, 
        messages: list[dict], 
        temperature: float = 0.5, 
        max_tokens: int = 768,
    ) -> str:
        """Не-потоковая генерация через Ollama /api/chat."""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "repeat_penalty": 1.1,
                        "top_p": 0.9,
                        "num_ctx": self.context_window,
                    },
                }
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("message", {}).get("content", "⚠️ Ответ не получен.")
        except Exception as e:
            logging.error(f"Ошибка при генерации Ollama: {e}")
            return "⚠️ Не удалось получить ответ. Пожалуйста, повторите запрос через несколько секунд."
    
    async def health_check(self) -> bool:
        """Проверить доступность Ollama API."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status == 200
        except Exception as e:
            logging.error(f"❌ Ollama недоступна: {e}")
            return False
    
    async def close(self) -> None:
        """Закрыть HTTP-сессию."""
        if self._session and not self._session.closed:
            await self._session.close()
