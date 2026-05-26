from abc import ABC, abstractmethod
from typing import AsyncIterator


class LLMProvider(ABC):
    """Абстрактный интерфейс для LLM-провайдеров.
    
    Все конкретные провайдеры (Ollama, OpenAI, Anthropic) реализуют этот интерфейс.
    Это позволяет переключать провайдера одной переменной ENV без изменения кода.
    """
    
    @abstractmethod
    async def chat_stream(
        self, 
        messages: list[dict], 
        temperature: float = 0.5, 
        max_tokens: int = 768,
    ) -> AsyncIterator[str]:
        """Потоковая генерация ответа. Yields: накопленный текст ответа."""
        ...
    
    @abstractmethod
    async def chat(
        self, 
        messages: list[dict], 
        temperature: float = 0.5, 
        max_tokens: int = 768,
    ) -> str:
        """Не-потоковая генерация ответа. Возвращает полный текст."""
        ...
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Проверка доступности провайдера."""
        ...
    
    @abstractmethod
    async def close(self) -> None:
        """Закрыть HTTP-сессии и освободить ресурсы."""
        ...
