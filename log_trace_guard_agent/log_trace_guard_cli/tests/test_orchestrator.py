"""Tests for ai_core/orchestrator.py"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from log_guard.ai_core.intent_classifier import IntentResult
from log_guard.ai_core.orchestrator import AIOrchestrator, get_orchestrator


class TestAIOrchestrator(unittest.TestCase):
    def setUp(self):
        self.orch = AIOrchestrator()

    def test_load_module_unknown_returns_none(self):
        result = self.orch._load_module("nonexistent_module")
        self.assertIsNone(result)

    def test_load_module_caches(self):
        mock_cls = MagicMock(return_value=MagicMock(name="mock_svc"))
        with patch.dict("sys.modules", {
            "log_guard.modules.log_parse": MagicMock(LogParseService=mock_cls),
        }):
            m1 = self.orch._load_module("log_parse")
            m2 = self.orch._load_module("log_parse")
            self.assertIs(m1, m2)

    def test_load_module_import_error(self):
        with patch("builtins.__import__", side_effect=ImportError("no module")):
            result = self.orch._load_module("log_parse")
            self.assertIsNone(result)

    @patch("log_guard.ai_core.orchestrator.get_context_manager")
    def test_call_module_returns_none_for_missing_module(self, mock_cm):
        mock_cm.return_value.current = MagicMock()
        intent = IntentResult("general", 0.9)
        result = self.orch._call_module(intent, "test")
        self.assertIsNone(result)

    @patch("log_guard.ai_core.orchestrator.get_context_manager")
    def test_has_meaningful_data_empty(self, mock_cm):
        self.assertFalse(self.orch._has_meaningful_data(None))
        self.assertFalse(self.orch._has_meaningful_data({}))

    @patch("log_guard.ai_core.orchestrator.get_context_manager")
    def test_has_meaningful_data_error(self, mock_cm):
        self.assertFalse(self.orch._has_meaningful_data({"error": "fail"}))

    @patch("log_guard.ai_core.orchestrator.get_context_manager")
    def test_has_meaningful_data_valid(self, mock_cm):
        data = {"parse": {"code": 0, "data": {"src_ip": "1.2.3.4"}}}
        self.assertTrue(self.orch._has_meaningful_data(data))

    @patch("log_guard.ai_core.orchestrator.get_polisher")
    @patch("log_guard.ai_core.orchestrator.get_rag")
    @patch("log_guard.ai_core.orchestrator.get_context_manager")
    @patch("log_guard.ai_core.orchestrator.get_classifier")
    def test_process_general_question(self, mock_cls, mock_cm, mock_rag, mock_polish):
        # Setup classifier
        intent = IntentResult("general", 0.5)
        mock_cls.return_value.classify.return_value = intent

        # Setup context
        ctx = MagicMock()
        ctx.get_recent_history.return_value = []
        mock_cm.return_value.get_or_create.return_value = ctx

        # Setup RAG
        mock_rag.return_value.search_text.return_value = ""

        # Setup polisher
        mock_polish.return_value.direct_answer.return_value = "通用回答"

        result = self.orch.process("什么是防火墙")
        self.assertEqual(result["response"], "通用回答")
        self.assertEqual(result["intent"], "general")
        self.assertFalse(result["has_module_result"])


class TestGetOrchestrator(unittest.TestCase):
    def test_singleton(self):
        a = get_orchestrator()
        b = get_orchestrator()
        self.assertIs(a, b)


if __name__ == "__main__":
    unittest.main()
