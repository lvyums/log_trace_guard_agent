"""Tests for ai_core/prompts.py"""
import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from log_guard.ai_core.prompts import (
    get_system_prompt, build_intent_messages, build_chat_messages,
    MODULE_PROMPTS, INTENT_CLASSIFIER_SYSTEM,
)


class TestGetSystemPrompt(unittest.TestCase):
    def test_known_modules(self):
        for module in MODULE_PROMPTS:
            prompt = get_system_prompt(module)
            self.assertIsInstance(prompt, str)
            self.assertTrue(len(prompt) > 50)

    def test_unknown_module_falls_to_general(self):
        prompt = get_system_prompt("unknown")
        self.assertEqual(prompt, MODULE_PROMPTS["general"])


class TestBuildIntentMessages(unittest.TestCase):
    def test_returns_list_of_dicts(self):
        msgs = build_intent_messages("test input")
        self.assertIsInstance(msgs, list)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[1]["role"], "user")
        self.assertIn("test input", msgs[1]["content"])

    def test_system_content_is_classifier_prompt(self):
        msgs = build_intent_messages("hi")
        self.assertEqual(msgs[0]["content"], INTENT_CLASSIFIER_SYSTEM)


class TestBuildChatMessages(unittest.TestCase):
    def test_basic(self):
        msgs = build_chat_messages("general", "hello")
        self.assertIsInstance(msgs, list)
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[-1]["role"], "user")
        self.assertIn("hello", msgs[-1]["content"])

    def test_with_rag_context(self):
        msgs = build_chat_messages("general", "q", rag_context="RAG info")
        # Should have system + rag + user
        self.assertGreaterEqual(len(msgs), 3)
        rag_msg = [m for m in msgs if "RAG" in m.get("content", "")]
        self.assertTrue(len(rag_msg) >= 1)

    def test_with_original_result(self):
        msgs = build_chat_messages(
            "log_parse", "q", original_result='{"risk": "high"}'
        )
        result_msg = [m for m in msgs if "业务模块" in m.get("content", "")]
        self.assertTrue(len(result_msg) >= 1)

    def test_with_history(self):
        history = [
            {"role": "user", "content": "prev q"},
            {"role": "assistant", "content": "prev a"},
        ]
        msgs = build_chat_messages("general", "new q", history=history)
        self.assertGreaterEqual(len(msgs), 3)

    def test_history_last_is_user_skips_duplicate(self):
        history = [{"role": "user", "content": "q"}]
        msgs = build_chat_messages("general", "q", history=history)
        user_msgs = [m for m in msgs if m["role"] == "user"]
        self.assertEqual(len(user_msgs), 1)


if __name__ == "__main__":
    unittest.main()
