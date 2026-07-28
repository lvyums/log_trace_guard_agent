"""Tests for ai_core/intent_classifier.py"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from log_guard.ai_core.intent_classifier import (
    IntentResult, IntentClassifier, INTENT_MODULES, get_classifier,
)


class TestIntentResult(unittest.TestCase):
    def test_default_values(self):
        r = IntentResult()
        self.assertEqual(r.intent, "general")
        self.assertEqual(r.confidence, 0.0)
        self.assertEqual(r.params, {})
        self.assertEqual(r.module, INTENT_MODULES["general"])

    def test_known_intent(self):
        r = IntentResult("log_parse", 0.9, {"log_line": "test"})
        self.assertEqual(r.intent, "log_parse")
        self.assertEqual(r.confidence, 0.9)
        self.assertEqual(r.module, "log_parse")

    def test_is_actionable_above_threshold(self):
        r = IntentResult("log_parse", 0.8)
        self.assertTrue(r.is_actionable)

    def test_is_actionable_below_threshold(self):
        r = IntentResult("log_parse", 0.1)
        self.assertFalse(r.is_actionable)

    def test_is_actionable_general_always_false(self):
        r = IntentResult("general", 0.99)
        self.assertFalse(r.is_actionable)

    def test_is_general(self):
        r = IntentResult("general", 0.5)
        self.assertTrue(r.is_general)

    def test_is_general_low_confidence(self):
        r = IntentResult("log_parse", 0.1)
        self.assertTrue(r.is_general)

    def test_repr(self):
        r = IntentResult("log_parse", 0.85)
        self.assertIn("log_parse", repr(r))
        self.assertIn("0.85", repr(r))


class TestIntentClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = IntentClassifier()

    @patch("log_guard.ai_core.intent_classifier.get_llm")
    def test_classify_empty_input(self, mock_llm):
        result = self.classifier.classify("")
        self.assertEqual(result.intent, "general")
        self.assertEqual(result.confidence, 0.0)
        mock_llm.assert_not_called()

    @patch("log_guard.ai_core.intent_classifier.get_llm")
    def test_classify_whitespace_input(self, mock_llm):
        result = self.classifier.classify("   ")
        self.assertEqual(result.intent, "general")
        mock_llm.assert_not_called()

    @patch("log_guard.ai_core.intent_classifier.get_llm")
    def test_classify_llm_failure(self, mock_llm):
        mock_llm.return_value.chat_json.return_value = {
            "success": False, "error": "timeout", "data": None,
        }
        result = self.classifier.classify("test input")
        self.assertEqual(result.intent, "general")
        self.assertIn("LLM 分类失败", result.reason)

    @patch("log_guard.ai_core.intent_classifier.get_llm")
    def test_classify_valid_response(self, mock_llm):
        mock_llm.return_value.chat_json.return_value = {
            "success": True, "error": None, "data": {
                "intent": "log_parse",
                "confidence": 0.95,
                "params": {"log_line": "Failed password"},
                "reason": "contains Failed password",
            },
        }
        result = self.classifier.classify("Failed password for root")
        self.assertEqual(result.intent, "log_parse")
        self.assertAlmostEqual(result.confidence, 0.95)
        self.assertEqual(result.params["log_line"], "Failed password")

    @patch("log_guard.ai_core.intent_classifier.get_llm")
    def test_classify_invalid_intent_falls_to_general(self, mock_llm):
        mock_llm.return_value.chat_json.return_value = {
            "success": True, "error": None, "data": {
                "intent": "unknown_intent",
                "confidence": 0.9,
                "params": {},
                "reason": "test",
            },
        }
        result = self.classifier.classify("test")
        self.assertEqual(result.intent, "general")
        self.assertEqual(result.confidence, 0.0)

    def test_intent_modules_mapping(self):
        expected = {
            "log_parse": "log_parse",
            "collection": "log_collect",
            "compliance": "compliance",
            "script_gen": "script_gen",
            "correlation": "log_correlate",
            "general": None,
        }
        self.assertEqual(INTENT_MODULES, expected)


class TestGetClassifier(unittest.TestCase):
    def test_singleton(self):
        a = get_classifier()
        b = get_classifier()
        self.assertIs(a, b)


if __name__ == "__main__":
    unittest.main()
