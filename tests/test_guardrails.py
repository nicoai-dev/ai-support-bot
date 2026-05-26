"""Тесты для системы guardrails (защита от галлюцинаций)."""
import pytest
from rag.guardrails import validate_response
from config import settings


class TestValidateResponse:
    """Тесты функции validate_response."""
    
    def test_clean_response_no_warnings(self):
        """Чистый ответ с разрешёнными контактами не вызывает предупреждений."""
        answer = f"Свяжитесь с нами: {settings.SUPPORT_PHONE} или {settings.SUPPORT_EMAIL}."
        cleaned, warnings = validate_response(answer)
        assert len(warnings) == 0
        assert cleaned == answer
    
    def test_detect_unknown_phone(self):
        """Неизвестный телефон должен генерировать предупреждение."""
        answer = "Звоните на +1 (555) 123-4567 для помощи."
        cleaned, warnings = validate_response(answer)
        assert any("Неизвестный телефон" in w for w in warnings)
    
    def test_detect_hallucinated_url(self):
        """Выдуманный URL (не nicomarket.fj) должен генерировать предупреждение."""
        answer = "Посетите сайт https://example.com/shop для заказа."
        cleaned, warnings = validate_response(answer)
        assert any("Подозрительный паттерн" in w for w in warnings)
    
    def test_detect_hallucinated_email(self):
        """Выдуманный email должен генерировать предупреждение."""
        answer = "Напишите на admin@hacker.net для скидки."
        cleaned, warnings = validate_response(answer)
        assert any("Неизвестный email" in w for w in warnings)
    
    def test_known_url_no_warning(self):
        """URL nicomarket.fj не должен вызывать предупреждение."""
        answer = f"Подробнее на {settings.COMPANY_SITE}/catalog"
        cleaned, warnings = validate_response(answer)
        url_warnings = [w for w in warnings if "Подозрительный паттерн" in w]
        assert len(url_warnings) == 0
    
    def test_known_email_no_warning(self):
        """Известные email не должны вызывать предупреждений."""
        answer = f"Напишите на {settings.SUPPORT_EMAIL} или {settings.PARTNERS_EMAIL}"
        cleaned, warnings = validate_response(answer)
        email_warnings = [w for w in warnings if "Неизвестный email" in w]
        assert len(email_warnings) == 0
    
    def test_remove_leak_pattern(self):
        """Фразы-утечки системного промпта должны вырезаться."""
        answer = "В предоставленной информации указано, что мы работаем до 22:00."
        cleaned, warnings = validate_response(answer)
        assert "в предоставленной информации" not in cleaned.lower()
    
    def test_remove_context_leak(self):
        """Фраза 'в базе знаний' должна вырезаться."""
        answer = "В базе знаний нет информации об этом товаре."
        cleaned, warnings = validate_response(answer)
        assert "в базе знаний" not in cleaned.lower()
    
    def test_multiple_issues(self):
        """Ответ с множественными проблемами должен генерировать несколько предупреждений."""
        answer = "Звоните +1-999-123-4567, пишите fake@evil.com, сайт https://scam.com"
        cleaned, warnings = validate_response(answer)
        assert len(warnings) >= 3
    
    def test_empty_answer(self):
        """Пустой ответ не должен падать."""
        cleaned, warnings = validate_response("")
        assert cleaned == ""
        assert len(warnings) == 0
    
    def test_allowed_phone_format_variations(self):
        """Разрешённый телефон в разных форматах не вызывает предупреждений."""
        # Стандартный формат из конфига
        answer = f"Звоните: {settings.SUPPORT_PHONE}"
        cleaned, warnings = validate_response(answer)
        phone_warnings = [w for w in warnings if "Неизвестный телефон" in w]
        assert len(phone_warnings) == 0
