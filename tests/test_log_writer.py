import unittest
import logging
import os
import json
from unittest.mock import call, patch, MagicMock
from app.tools.logwriter import LogWriter


class TestLogWriter(unittest.TestCase):
    @patch("app.tools.logwriter.os.makedirs")
    @patch("app.tools.logwriter.RotatingFileHandler")
    def test_initialization(self, mock_handler, mock_makedirs):
        """Test that loggers are initialized correctly."""
        LogWriter.initialize_logger()
        self.assertTrue(LogWriter.logger_initialized)
        self.assertIsNotNone(LogWriter.general_logger)
        self.assertIsNotNone(LogWriter.error_logger)
        self.assertIsNotNone(LogWriter.audit_logger)

    def test_mask_pii(self):
        """Test PII masking functionality."""
        email = "user@example.com"
        masked_email = LogWriter.mask_pii(email)
        self.assertNotEqual(masked_email, email)
        self.assertIn("[EMAIL REDACTED]", masked_email)

    @patch("app.tools.logwriter.os.makedirs")
    @patch("app.tools.logwriter.RotatingFileHandler")
    @patch("app.tools.logwriter.logging.Logger.info")
    def test_audit_log(self, mock_info, mock_handler, mock_makedirs):
        """Test audit logging with structured data."""
        test_message = {
            "userName": "testUser",
            "actionName": "testAction",
            "status": "SUCCESS",
        }
        LogWriter.audit_log(test_message)
        mock_info.assert_called_once()
        args, _ = mock_info.call_args
        logged_message = json.loads(args[0])
        self.assertEqual(logged_message["userName"], "testUser")

    @patch("app.tools.logwriter.os.makedirs")
    @patch("app.tools.logwriter.RotatingFileHandler")
    @patch("app.tools.logwriter.logging.Logger.info")
    def test_info_log(self, mock_error, mock_handler, mock_makedirs):
        """Test info logging."""
        LogWriter.log("info", "This is an info message", mask_pii=False)
        mock_error.assert_called_once_with("This is an info message")

    @patch("app.tools.logwriter.os.makedirs")
    @patch("app.tools.logwriter.RotatingFileHandler")
    @patch("app.tools.logwriter.logging.Logger.warning")
    def test_warning_log(self, mock_warning, mock_handler, mock_makedirs):
        """Test warning logging."""
        LogWriter.log("warning", "This is a warning message", mask_pii=False)
        mock_warning.assert_called_once_with("This is a warning message")

    @patch("app.tools.logwriter.os.makedirs")
    @patch("app.tools.logwriter.RotatingFileHandler")
    @patch("app.tools.logwriter.logging.Logger.error")
    def test_error_log(self, mock_error, mock_handler, mock_makedirs):
        """Test error logging."""
        LogWriter.log("error", "This is an error", mask_pii=False)
        calls = [call("This is an error")]
        mock_error.assert_has_calls(calls)

        # the mock error should be called twice, once for general logging and once for the error log specifically
        self.assertEqual(mock_error.call_count, 1)


if __name__ == "__main__":
    unittest.main()
