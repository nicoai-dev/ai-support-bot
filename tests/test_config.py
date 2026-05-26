"""Тесты конфигурации."""
import pytest
from config import settings


class TestSettings:
    
    def test_settings_loads(self):
        """Конфиг загружается без ошибок."""
        assert settings.BOT_TOKEN is not None
        assert len(settings.BOT_TOKEN) > 0
    
    def test_default_env_is_dev(self):
        """По умолчанию ENV=dev."""
        assert settings.ENV in ("dev", "staging", "prod")
    
    def test_contacts_not_empty(self):
        """Контактные данные заполнены."""
        assert settings.SUPPORT_PHONE
        assert settings.SUPPORT_EMAIL
        assert settings.COMPANY_SITE
    
    def test_known_emails_property(self):
        """known_emails содержит все email-адреса."""
        emails = settings.known_emails
        assert settings.SUPPORT_EMAIL in emails
        assert settings.PARTNERS_EMAIL in emails
        assert settings.PRESS_EMAIL in emails
    
    def test_known_contacts_property(self):
        """known_contacts содержит все контакты."""
        contacts = settings.known_contacts
        assert "phone" in contacts
        assert "email_support" in contacts
        assert contacts["phone"] == settings.SUPPORT_PHONE
    
    def test_is_dev_property(self):
        """Свойство is_dev работает."""
        # В тестовом окружении обычно dev
        assert isinstance(settings.is_dev, bool)
    
    def test_llm_provider_valid(self):
        """LLM_PROVIDER имеет допустимое значение."""
        assert settings.LLM_PROVIDER in ("ollama", "openai", "anthropic")
