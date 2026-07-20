"""Tests for ai_core/polisher.py"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from log_guard.ai_core.polisher import ResponsePolisher, get_polisher


class TestResponsePolisher(unittest.TestCase):
    def setUp(self):
        self.polisher = ResponsePolisher()

    def test_polish_empty_result(self):
        result = self.polisher.polish("log_parse", "test", {})
        self.assertEqual(result, "暂无返回结果。")

    def test_polish_none_result(self):
        result = self.polisher.polish("log_parse", "test", None)
        self.assertEqual(result, "暂无返回结果。")

    @patch("log_guard.ai_core.polisher.get_llm")
    def test_polish_success(self, mock_llm):
        mock_llm.return_value.chat.return_value = {
            "success": True, "content": "分析结果：无风险", "error": None,
        }
        result = self.polisher.polish(
            "log_parse", "分析日志", {"risk": "low"}
        )
        self.assertEqual(result, "分析结果：无风险")

    @patch("log_guard.ai_core.polisher.get_llm")
    def test_polish_llm_failure_returns_raw(self, mock_llm):
        mock_llm.return_value.chat.return_value = {
            "success": False, "content": None, "error": "timeout",
        }
        result = self.polisher.polish(
            "log_parse", "test", {"data": "value"}
        )
        self.assertIn("智能解读不可用", result)
        self.assertIn("data", result)

    @patch("log_guard.ai_core.polisher.get_llm")
    def test_direct_answer_success(self, mock_llm):
        mock_llm.return_value.chat.return_value = {
            "success": True, "content": "SQL注入是一种攻击手段", "error": None,
        }
        result = self.polisher.direct_answer("什么是SQL注入")
        self.assertEqual(result, "SQL注入是一种攻击手段")

    @patch("log_guard.ai_core.polisher.get_llm")
    def test_direct_answer_llm_failure_with_rag(self, mock_llm):
        mock_llm.return_value.chat.return_value = {
            "success": False, "content": None, "error": "error",
        }
        result = self.polisher.direct_answer(
            "test", rag_context="RAG结果内容"
        )
        self.assertIn("基于知识库检索结果", result)
        self.assertIn("RAG结果内容", result)

    @patch("log_guard.ai_core.polisher.get_llm")
    def test_direct_answer_llm_failure_no_rag(self, mock_llm):
        mock_llm.return_value.chat.return_value = {
            "success": False, "content": None, "error": "连接失败",
        }
        result = self.polisher.direct_answer("test")
        self.assertIn("LLM 暂时不可用", result)
        self.assertIn("连接失败", result)


class TestGetPolisher(unittest.TestCase):
    def test_singleton(self):
        a = get_polisher()
        b = get_polisher()
        self.assertIs(a, b)


if __name__ == "__main__":
    unittest.main()
