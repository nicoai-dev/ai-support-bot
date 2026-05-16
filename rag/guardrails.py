import re
import logging

# Факты, которые бот НЕ ДОЛЖЕН выдумывать — проверяем на соответствие базе
KNOWN_CONTACTS = {
    "phone": "+679 764-2658",
    "email_support": "support@nicomarket.fj",
    "email_partners": "partners@nicomarket.fj",
    "email_press": "press@nicomarket.fj",
    "site": "https://nicomarket.fj",
    "telegram": "@NicoMarketOfficial",
    "instagram": "@nicomarket.fj",
}

# Паттерны потенциальных галлюцинаций
HALLUCINATION_PATTERNS = [
    # Выдуманные URL
    r"https?://(?!nicomarket\.fj)\S+",
    # Выдуманные email
    r"[\w.-]+@(?!nicomarket\.fj)\w+\.\w+",
    # Выдуманные телефоны (не наш)
    r"\+\d[\d\s()-]{8,}(?<!\+679 764-2658)",
    # Упоминание «сайта» без конкретной ссылки из базы
    r"(?:на нашем сайте|на сайте|проверьте на сайте|зайдите на сайт)(?!.*nicomarket\.fj)",
    # Слова-маркеры утечки механики
    r"(?:в предоставленн|согласно инструкц|в моей базе|мои данные|в контексте)",
]

def validate_response(answer: str) -> tuple[str, list[str]]:
    """
    Проверяет ответ на потенциальные галлюцинации.
    Возвращает (очищенный_ответ, список_предупреждений).
    """
    warnings = []
    cleaned = answer
    
    for pattern in HALLUCINATION_PATTERNS:
        matches = re.findall(pattern, cleaned, re.IGNORECASE)
        if matches:
            warnings.append(f"Подозрительный паттерн: {pattern} -> {matches}")
            logging.warning(f"⚠️ Guardrail: найден подозрительный паттерн в ответе: {matches}")
    
    # Проверка: если упомянут телефон, он должен быть наш
    phone_matches = re.findall(r"\+\d[\d\s()-]{6,}", cleaned)
    for phone in phone_matches:
        normalized = re.sub(r"[\s()-]", "", phone)
        # Убираем пробелы и символы для сравнения с +6797642658
        if normalized not in ["+6797642658"]:
            warnings.append(f"Неизвестный телефон в ответе: {phone}")
            logging.warning(f"⚠️ Guardrail: неизвестный телефон: {phone}")
    
    # Проверка: если упомянут email, он должен быть из KNOWN_CONTACTS
    email_matches = re.findall(r"[\w.-]+@[\w.-]+\.\w+", cleaned)
    known_emails = {v for k, v in KNOWN_CONTACTS.items() if "email" in k}
    for email in email_matches:
        if email not in known_emails:
            warnings.append(f"Неизвестный email: {email}")
            logging.warning(f"⚠️ Guardrail: неизвестный email: {email}")
    
    return cleaned, warnings
