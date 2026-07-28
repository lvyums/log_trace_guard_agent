"""Tests for ai_core/context.py"""
import os
import sys
import time
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from log_guard.ai_core.context import ConversationContext, ContextManager, get_context_manager


class TestConversationContext(unittest.TestCase):
    def setUp(self):
        self.ctx = ConversationContext("test-session")

    def test_init(self):
        self.assertEqual(self.ctx.session_id, "test-session")
        self.assertEqual(self.ctx.history, [])
        self.assertIsNone(self.ctx.last_intent)
        self.assertIsNone(self.ctx.last_module_result)

    def test_add_turn(self):
        self.ctx.add_turn("user", "hello")
        self.assertEqual(len(self.ctx.history), 1)
        self.assertEqual(self.ctx.history[0]["role"], "user")
        self.assertEqual(self.ctx.history[0]["content"], "hello")
        self.assertIn("timestamp", self.ctx.history[0])

    def test_add_multiple_turns(self):
        self.ctx.add_turn("user", "q1")
        self.ctx.add_turn("assistant", "a1")
        self.ctx.add_turn("user", "q2")
        self.assertEqual(len(self.ctx.history), 3)

    def test_get_recent_history(self):
        self.ctx.add_turn("user", "q1")
        self.ctx.add_turn("assistant", "a1")
        self.ctx.add_turn("user", "q2")
        self.ctx.add_turn("assistant", "a2")

        recent = self.ctx.get_recent_history(2)
        # 2 turns = 4 messages
        self.assertEqual(len(recent), 4)
        self.assertEqual(recent[-1]["content"], "a2")

    def test_get_recent_history_empty(self):
        self.assertEqual(self.ctx.get_recent_history(3), [])

    def test_clear(self):
        self.ctx.add_turn("user", "hello")
        self.ctx.last_intent = "log_parse"
        self.ctx.clear()

        self.assertEqual(self.ctx.history, [])
        self.assertIsNone(self.ctx.last_intent)
        self.assertIsNone(self.ctx.last_module_result)

    def test_to_dict(self):
        self.ctx.add_turn("user", "hello")
        self.ctx.last_intent = "log_parse"
        self.ctx.last_log_file = "/var/log/auth.log"

        d = self.ctx.to_dict()
        self.assertEqual(d["session_id"], "test-session")
        self.assertEqual(d["last_intent"], "log_parse")
        self.assertEqual(d["last_log_file"], "/var/log/auth.log")
        self.assertEqual(len(d["history"]), 1)

    def test_history_truncation(self):
        """Test that history is truncated at max_context_turns * 2."""
        # Add more than the default max (20 turns = 40 messages)
        max_turns = 20
        for i in range(max_turns + 5):
            self.ctx.add_turn("user", f"q{i}")
            self.ctx.add_turn("assistant", f"a{i}")
        self.assertLessEqual(len(self.ctx.history), max_turns * 2)

    def test_timestamps(self):
        before = time.time()
        self.ctx.add_turn("user", "hello")
        after = time.time()
        ts = self.ctx.history[0]["timestamp"]
        self.assertGreaterEqual(ts, before)
        self.assertLessEqual(ts, after)


class TestContextManager(unittest.TestCase):
    def setUp(self):
        self.cm = ContextManager()

    def test_new_session(self):
        ctx = self.cm.new_session("my-session")
        self.assertEqual(ctx.session_id, "my-session")
        self.assertIs(self.cm.current, ctx)

    def test_new_session_auto_id(self):
        ctx = self.cm.new_session()
        self.assertIsNotNone(ctx.session_id)
        self.assertTrue(ctx.session_id.startswith("session_"))

    def test_get_or_create_new(self):
        ctx = self.cm.get_or_create()
        self.assertIsNotNone(ctx)
        self.assertIs(self.cm.current, ctx)

    def test_get_or_create_existing(self):
        first = self.cm.new_session("existing")
        second = self.cm.get_or_create("existing")
        self.assertIs(first, second)

    def test_get_or_create_no_id(self):
        first = self.cm.new_session("s1")
        second = self.cm.get_or_create()
        self.assertIs(first, second)

    def test_clear_current(self):
        self.cm.new_session()
        self.cm.current.add_turn("user", "hello")
        self.assertEqual(len(self.cm.current.history), 1)
        self.cm.clear_current()
        self.assertEqual(len(self.cm.current.history), 0)

    def test_current_is_none_when_no_session(self):
        self.assertIsNone(self.cm.current)

    def test_save_chat_log(self):
        """Test save_chat_log creates a file."""
        self.cm.new_session()
        self.cm.current.add_turn("user", "hello")
        self.cm.current.add_turn("assistant", "hi")
        self.cm.save_chat_log()
        # Should not raise - file has been saved

    def test_save_chat_log_empty(self):
        """save_chat_log should not raise if no session or no history."""
        self.cm.save_chat_log()  # No session
        self.cm.new_session()
        self.cm.save_chat_log()  # Empty history

    def test_get_context_manager_singleton(self):
        a = get_context_manager()
        b = get_context_manager()
        self.assertIs(a, b)


if __name__ == "__main__":
    unittest.main()