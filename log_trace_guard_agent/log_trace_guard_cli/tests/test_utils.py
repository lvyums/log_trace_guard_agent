"""Tests for common/utils.py"""
import json
import os
import sys
import tempfile
import unittest

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from log_guard.common.utils import (
    Result,
    JsonConfigLoader,
    LogManager,
    clean_syslog_prefix,
    normalize_whitespace,
    is_gibberish,
    extract_ip_from_str,
    truncate,
    clean_special_chars,
    DATA_DIR,
)


class TestResult(unittest.TestCase):
    def test_ok(self):
        r = Result.ok({"a": 1}, "done")
        self.assertEqual(r["code"], 0)
        self.assertEqual(r["msg"], "done")
        self.assertEqual(r["data"], {"a": 1})
        self.assertIn("timestamp", r)

    def test_ok_default_data(self):
        r = Result.ok()
        self.assertEqual(r["data"], {})

    def test_fail(self):
        r = Result.fail("bad", 500)
        self.assertEqual(r["code"], 500)
        self.assertEqual(r["msg"], "bad")
        self.assertEqual(r["data"], {})

    def test_fail_default_code(self):
        r = Result.fail("error")
        self.assertEqual(r["code"], 400)

    def test_from_exception(self):
        r = Result.from_exception(403, "forbidden")
        self.assertEqual(r["code"], 403)
        self.assertEqual(r["msg"], "forbidden")


class TestJsonConfigLoader(unittest.TestCase):
    def setUp(self):
        # Clear cache to avoid cross-test pollution
        JsonConfigLoader.clear_cache()

    def test_singleton(self):
        a = JsonConfigLoader()
        b = JsonConfigLoader()
        self.assertIs(a, b)

    def test_load_risk_rules(self):
        """Load a real JSON file from the project's data directory."""
        cfg = JsonConfigLoader.load("risk_rules.json")
        # risk_rules.json is a list of rule objects
        self.assertIsInstance(cfg, list)
        self.assertGreater(len(cfg), 0)
        self.assertIn("rule_id", cfg[0])
        self.assertIn("risk_level", cfg[0])

    def test_load_log_features(self):
        cfg = JsonConfigLoader.load("log_features.json")
        self.assertIsInstance(cfg, dict)
        self.assertGreater(len(cfg), 0, "log_features.json should have device types")

    def test_get_nonexistent_key(self):
        val = JsonConfigLoader.get("risk_rules.json", "nonexistent_key", default="fallback")
        self.assertEqual(val, "fallback")

    def test_get_dot_notation(self):
        """Test dot-notation key access."""
        cfg = JsonConfigLoader.load("risk_rules.json")
        if isinstance(cfg, dict):
            top_key = next(iter(cfg.keys()))
            # The get method with single key should work
            val = JsonConfigLoader.get("risk_rules.json", top_key)
            self.assertIsNotNone(val)

    def test_clear_cache(self):
        JsonConfigLoader.load("risk_rules.json")
        JsonConfigLoader.clear_cache()
        # Should reload without error
        cfg = JsonConfigLoader.load("risk_rules.json")
        self.assertIsInstance(cfg, list)

    def test_load_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            JsonConfigLoader.load("nonexistent_file.json")

    def test_data_dir_exists(self):
        self.assertTrue(os.path.isdir(DATA_DIR), f"DATA_DIR does not exist: {DATA_DIR}")

    def test_cache_returns_same_object(self):
        a = JsonConfigLoader.load("risk_rules.json")
        b = JsonConfigLoader.load("risk_rules.json")
        self.assertIs(a, b)  # Cached reference


class TestStrUtil(unittest.TestCase):
    def test_clean_syslog_prefix(self):
        self.assertEqual(clean_syslog_prefix("Mar 15 10:30:25 server test"), "test")

    def test_clean_syslog_priority(self):
        self.assertEqual(
            clean_syslog_prefix("<13>Mar 15 10:30:25 server test"),
            "test",
        )

    def test_clean_syslog_iso(self):
        result = clean_syslog_prefix("2024-03-15T10:30:25.123+08:00 hostname test")
        self.assertEqual(result, "test")

    def test_normalize_whitespace(self):
        self.assertEqual(normalize_whitespace("a   b   c"), "a b c")
        self.assertEqual(normalize_whitespace("  hello  world  "), "hello world")

    def test_is_gibberish_empty(self):
        self.assertTrue(is_gibberish(""))

    def test_is_gibberish_normal(self):
        self.assertFalse(is_gibberish("normal text"))

    def test_is_gibberish_mostly_nonprintable(self):
        self.assertTrue(is_gibberish("\x00\x01\x02\x03\x04"))

    def test_extract_ip_from_str(self):
        self.assertEqual(extract_ip_from_str("from 192.168.1.1 request"), "192.168.1.1")

    def test_extract_ip_from_str_no_ip(self):
        self.assertIsNone(extract_ip_from_str("no ip here"))

    def test_extract_ip_from_str_multiple(self):
        result = extract_ip_from_str("from 10.0.0.1 to 10.0.0.2")
        self.assertEqual(result, "10.0.0.1")  # First IP

    def test_truncate_short(self):
        self.assertEqual(truncate("short", 100), "short")

    def test_truncate_long(self):
        result = truncate("hello world", 5)
        self.assertIn("hello", result)
        self.assertIn("...", result)

    def test_clean_special_chars(self):
        result = clean_special_chars("hello\x00world\x01test")
        self.assertEqual(result, "helloworldtest")

    def test_clean_special_chars_line_endings(self):
        result = clean_special_chars("line1\r\nline2\rline3")
        self.assertEqual(result, "line1\nline2\nline3")


class TestLogManager(unittest.TestCase):
    def test_get_logger(self):
        logger = LogManager.get_logger("test_smoke")
        self.assertIsNotNone(logger)

    def test_logger_singleton(self):
        a = LogManager()
        b = LogManager()
        self.assertIs(a, b)

    def test_log_parse_failure(self):
        # Should not raise
        LogManager.log_parse_failure("raw line here", context="test line")


if __name__ == "__main__":
    unittest.main()