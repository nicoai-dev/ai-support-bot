import logging
from config import settings
from llm.base import LLMProvider


def create_provider() -> LLMProvider:
    """Фабрика создания LLM-провайдера на основе настроек конфига.
    
    Выбирает провайдер по значению settings.LLM_PROVIDER:
    - "ollama" → OllamaProvider (локальная модель)
    - "openai" → OpenAIProvider (OpenAI API или совместимые)
    - "anthropic" → через OpenAI-совместимый клиент (TODO: нативный)
    """
    provider_name = settings.LLM_PROVIDER
    
    if provider_name == "ollama":
        from llm.ollama_provider import OllamaProvider
        logging.info(f"🤖 LLM Provider: Ollama ({settings.OLLAMA_MODEL})")
        return OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout=settings.OLLAMA_TIMEOUT,
            context_window=settings.LLM_CONTEXT_WINDOW,
        )
    
    elif provider_name == "openai":
        from llm.openai_provider import OpenAIProvider
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY не задан! Установите его в .env")
        logging.info(f"🤖 LLM Provider: OpenAI ({settings.OPENAI_MODEL})")
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_BASE_URL,
            timeout=settings.OPENAI_TIMEOUT,
        )
    
    elif provider_name == "anthropic":
        # Anthropic через OpenAI-совместимый интерфейс (работает через base_url proxy)
        # TODO: заменить на нативный anthropic SDK при необходимости
        from llm.openai_provider import OpenAIProvider
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY не задан! Установите его в .env")
        logging.info(f"🤖 LLM Provider: Anthropic ({settings.ANTHROPIC_MODEL})")
        return OpenAIProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.ANTHROPIC_MODEL,
            base_url="https://api.anthropic.com/v1",
            timeout=settings.ANTHROPIC_TIMEOUT,
        )
    
    else:
        raise ValueError(f"Неизвестный LLM_PROVIDER: {provider_name}. Допустимые: ollama, openai, anthropic")
