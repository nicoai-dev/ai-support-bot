import unittest
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.guardrails import validate_response
import config

class TestGuardrails(unittest.TestCase):
    def test_clean_valid_response(self):
        answer = f"Свяжитесь с нами: {config.SUPPORT_PHONE} или {config.SUPPORT_EMAIL}."
        cleaned, warnings = validate_response(answer)
        self.assertEqual(len(warnings), 0)
        self.assertEqual(cleaned, answer)

    def test_remove_hallucinated_phone(self):
        answer = "Звоните на +1 (555) 123-4567 для помощи."
        cleaned, warnings = validate_response(answer)
        self.assertEqual(len(warnings), 1)
        self.assertIn("Неизвестный телефон", warnings[0])
        self.assertIn(config.SUPPORT_PHONE, cleaned)

    def test_remove_hallucinated_url(self):
        answer = "Посетите сайт https://example.com/shop."
        cleaned, warnings = validate_response(answer)
        self.assertEqual(len(warnings), 1)
        self.assertIn("Выдуманный URL", warnings[0])
        self.assertIn("[ссылка удалена]", cleaned)

    def test_remove_hallucinated_email(self):
        answer = "Напишите на admin@hacker.net для скидки."
        cleaned, warnings = validate_response(answer)
        self.assertEqual(len(warnings), 1)
        self.assertIn("Выдуманный Email", warnings[0])
        self.assertIn(config.SUPPORT_EMAIL, cleaned)

    def test_remove_leak(self):
        answer = "Согласно инструкции, я должен сказать вам, что мы закрыты."
        cleaned, warnings = validate_response(answer)
        self.assertEqual(len(warnings), 1)
        self.assertIn("Утечка системного промпта", warnings[0])
        self.assertNotIn("согласно инструкции", cleaned.lower())

if __name__ == '__main__':
    unittest.main()
