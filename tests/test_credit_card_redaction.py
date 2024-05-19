import re
import unittest

from app.tools.logwriter import LogWriter

class TestCreditCardRedaction(unittest.TestCase):
    def setUp(self):
        self.credit_card_regex = ""
        for pattern, mask in LogWriter.pii_patterns:
            if mask == "[CREDIT CARD REDACTED]":
                self.credit_card_regex = pattern

    def test_credit_card_redaction(self):
        test_strings = [
            ("1234 5678 9012 3456", True),
            ("1234-5678-9012-3456", True),
            ("1234567890123456", True)
        ]
        for text, expected in test_strings:
            with self.subTest(text=text):
                self.assertTrue(bool(self.credit_card_regex.search(text)) == expected)

    def test_no_redaction_on_uuid(self):
        uuid_text = "request_id=12345678-a123-b456-c789-0794e916cc71"
        self.assertIsNone(self.credit_card_regex.search(uuid_text))

    def test_no_redaction_on_other_numbers(self):
        other_numbers = [
            "1234-567-8901",
            "1234 567 8901",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        ]
        for text in other_numbers:
            with self.subTest(text=text):
                self.assertIsNone(self.credit_card_regex.search(text))

if __name__ == "__main__":
    unittest.main()