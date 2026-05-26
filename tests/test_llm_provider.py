"""Тесты LLM Provider абстракции."""
import pytest
from llm.base import LLMProvider
from llm.factory import create_provider
from llm.ollama_provider import OllamaProvider


class TestLLMFactory:
    
    def test_create_provider_returns_instance(self):
        """Фабрика возвращает LLMProvider."""
        provider = create_provider()
        assert isinstance(provider, LLMProvider)
    
    def test_ollama_provider_default(self):
        """По умолчанию создаётся OllamaProvider."""
        provider = create_provider()
        assert isinstance(provider, OllamaProvider)
    
    def test_ollama_provider_attributes(self):
        """OllamaProvider имеет нужные атрибуты."""
        from config import settings
        provider = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
        )
        assert provider.base_url == settings.OLLAMA_BASE_URL
        assert provider.model == settings.OLLAMA_MODEL


class TestLLMProviderInterface:
    
    def test_base_is_abstract(self):
        """LLMProvider нельзя инстанцировать напрямую."""
        with pytest.raises(TypeError):
            LLMProvider()
