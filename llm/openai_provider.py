import logging
from typing import AsyncIterator
from llm.base import LLMProvider

try:
    from openai import AsyncOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class OpenAIProvider(LLMProvider):
    """LLM-провайдер для OpenAI-совместимых API (OpenAI, Azure, Together, и т.д.)."""
    
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1", timeout: int = 120):
        if not HAS_OPENAI:
            raise ImportError(
                "Для использования OpenAI провайдера установите пакет openai: "
                "pip install openai"
            )
        self.model = model
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
    
    async def chat_stream(
        self, 
        messages: list[dict], 
        temperature: float = 0.5, 
        max_tokens: int = 768,
    ) -> AsyncIterator[str]:
        """Потоковая генерация через OpenAI Chat Completions API."""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            full_content = ""
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    full_content += delta
                    yield full_content
        except Exception as e:
            logging.error(f"Ошибка при потоковой генерации OpenAI: {e}")
            yield "⚠️ Не удалось получить ответ. Пожалуйста, повторите запрос через несколько секунд."
    
    async def chat(
        self, 
        messages: list[dict], 
        temperature: float = 0.5, 
        max_tokens: int = 768,
    ) -> str:
        """Не-потоковая генерация через OpenAI Chat Completions API."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or "⚠️ Ответ не получен."
        except Exception as e:
            logging.error(f"Ошибка при генерации OpenAI: {e}")
            return "⚠️ Не удалось получить ответ. Пожалуйста, повторите запрос через несколько секунд."
    
    async def health_check(self) -> bool:
        """Проверить доступность OpenAI API (лёгкий запрос)."""
        try:
            await self.client.models.list()
            return True
        except Exception as e:
            logging.error(f"❌ OpenAI API недоступен: {e}")
            return False
    
    async def close(self) -> None:
        """Закрыть HTTP-клиент."""
        await self.client.close()
