import re
import logging

# Контактные данные загружаются из централизованного конфига
from config import settings

KNOWN_CONTACTS = settings.known_contacts

# Получаем домен из конфига для динамических regex
_site_domain = settings.COMPANY_SITE.replace("https://", "").replace("http://", "").replace("/", "")
_escaped_domain = re.escape(_site_domain)

HALLUCINATION_PATTERNS = [
    # Выдуманные URL (кроме нашего домена)
    rf"https?://(?!{_escaped_domain})\S+",
    # Выдуманные email (кроме нашего домена)
    rf"[\w.-]+@(?!{_escaped_domain})\w+\.\w+",
    # Упоминание «сайта» без конкретной ссылки из базы
    rf"(?:на нашем сайте|на сайте|проверьте на сайте|зайдите на сайт)(?!.*{_escaped_domain})",
    # Выдуманные номера заказов (мы не генерируем номера)
    r"(?:заказ|order)\s*#?\s*\d{5,}",
]

LEAK_PATTERNS = [
    r"(?i)\bв\s+предоставленной\s+информации\b\s*",
    r"(?i)\bв\s+текущей\s+информации\b\s*",
    r"(?i)\bсогласно\s+информации\b\s*",
    r"(?i)\bсогласно\s+контексту\b\s*",
    r"(?i)\bв\s+контексте\b\s*",
    r"(?i)\bв\s+базе\s+знаний\b\s*",
    r"(?i)\bв\s+базе\b\s*",
    r"(?i)\bв\s+моих\s+данных\b\s*",
    r"(?i)\bмои\s+инструкции\b\s*",
    r"(?i)\bв\s+предоставленном\s+тексте\b\s*",
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
            
    for pattern in LEAK_PATTERNS:
        matches = re.findall(pattern, cleaned)
        if matches:
            logging.warning(f"⚠️ Guardrail: вырезана системная фраза: {matches}")
            # Для фраз, которые содержат 'нет' или 'не содержит', мы должны быть осторожнее, 
            # но простая замена часто работает, или мы можем просто вырезать саму отсылку.
            # Более надежно вырезать только саму фразу:
            cleaned = re.sub(pattern, "", cleaned)
    
    # Проверка: если упомянут телефон, он должен быть из разрешенного списка
    # \d гарантирует, что номер заканчивается цифрой (не открытой скобкой типа "(08")
    phone_matches = re.findall(r"\+[\d\s()-]{6,16}\d", cleaned)
    # Нормализуем телефон из конфига для сравнения
    allowed_normalized_phones = [re.sub(r"[\s()-]", "", settings.SUPPORT_PHONE)]
    
    for phone in phone_matches:
        normalized = re.sub(r"[\s()-]", "", phone)
        if normalized not in allowed_normalized_phones:
            warnings.append(f"Неизвестный телефон в ответе: {phone}")
            logging.warning(f"⚠️ Guardrail: неизвестный телефон: {phone}")
    
    # Проверка: если упомянут email, он должен быть из KNOWN_CONTACTS
    email_matches = re.findall(r"[\w.-]+@[\w.-]+\.\w+", cleaned)
    known_emails = settings.known_emails
    for email in email_matches:
        if email not in known_emails:
            warnings.append(f"Неизвестный email: {email}")
            logging.warning(f"⚠️ Guardrail: неизвестный email: {email}")
    
    return cleaned, warnings
