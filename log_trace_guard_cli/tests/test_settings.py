"""Tests for ai_core/settings.py"""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, PropertyMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)



class TestAISettings(unittest.TestCase):
    def setUp(self):
        # Save original env vars
        self._saved_env = {}
        for key in ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_NAME"]:
            self._saved_env[key] = os.environ.get(key)

        # Clear env vars for clean test
        for key in self._saved_env:
            if key in os.environ:
                del os.environ[key]

    def tearDown(self):
        # Restore original env vars
        for key, val in self._saved_env.items():
            if val is not None:
                os.environ[key] = val
            elif key in os.environ:
                del os.environ[key]

    def _make_settings(self):
        """Create a clean AISettings with no file-based config loading."""
        from log_guard.ai_core.settings import AISettings
        with patch.object(AISettings, '_load_from_dotenv'), \
             patch.object(AISettings, '_load_from_config_json'):
            s = AISettings()
        return s

    def test_default_values(self):
        """Test settings have sensible defaults."""
        s = self._make_settings()
        self.assertEqual(s.llm_api_key, "")
        self.assertEqual(s.llm_base_url, "https://raytoken.com.cn/v1")
        self.assertEqual(s.llm_model_name, "deepseek-v4-flash")
        self.assertFalse(s.is_configured)

    def test_configured_after_setting_key(self):
        s = self._make_settings()
        s.llm_api_key = "test-key"
        self.assertTrue(s.is_configured)

    def test_env_var_overrides(self):
        os.environ["LLM_API_KEY"] = "env-key"
        os.environ["LLM_BASE_URL"] = "https://env.example.com/v1"
        from log_guard.ai_core.settings import AISettings
        with patch.object(AISettings, '_load_from_dotenv'), \
             patch.object(AISettings, '_load_from_config_json'):
            s = AISettings()
        self.assertEqual(s.llm_api_key, "env-key")
        self.assertEqual(s.llm_base_url, "https://env.example.com/v1")

    def test_env_var_int_override(self):
        os.environ["LLM_TIMEOUT"] = "60"
        os.environ["LLM_MAX_TOKENS"] = "4096"
        s = self._make_settings()
        self.assertEqual(s.llm_timeout, 60)
        self.assertEqual(s.llm_max_tokens, 4096)

    def test_env_var_float_override(self):
        os.environ["LLM_TEMPERATURE"] = "0.5"
        s = self._make_settings()
        self.assertEqual(s.llm_temperature, 0.5)

    def test_save_and_load_config(self):
        """Test round-trip save and load from config.json."""
        s = self._make_settings()
        s.llm_api_key = "saved-key"
        s.llm_base_url = "https://saved.example.com/v1"
        s.llm_model_name = "saved-model"

        config_path = s.save_config()
        self.assertTrue(os.path.isfile(config_path))

        try:
            # Verify file content
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["llm_api_key"], "saved-key")
            self.assertEqual(data["llm_base_url"], "https://saved.example.com/v1")
            self.assertEqual(data["llm_model_name"], "saved-model")
        finally:
            if os.path.isfile(config_path):
                os.remove(config_path)

    def test_config_dir_creation(self):
        s = self._make_settings()
        config_dir = s.config_dir
        self.assertTrue(os.path.isdir(config_dir))
        # Should not raise
        self.assertIn(".log-guard", config_dir)

    def test_chat_log_dir_path(self):
        s = self._make_settings()
        path = s.chat_log_dir_path
        self.assertTrue(os.path.isdir(path))

    def test_vector_cache_path(self):
        s = self._make_settings()
        path = s.vector_cache_path
        self.assertIn("rule_vector_cache.json", path)

    def test_apply_dict(self):
        s = self._make_settings()
        s._apply_dict({
            "llm_api_key": "dict-key",
            "llm_temperature": 0.8,
            "llm_timeout": 45,
        })
        self.assertEqual(s.llm_api_key, "dict-key")
        self.assertEqual(s.llm_temperature, 0.8)
        self.assertEqual(s.llm_timeout, 45)


if __name__ == "__main__":
    unittest.main()