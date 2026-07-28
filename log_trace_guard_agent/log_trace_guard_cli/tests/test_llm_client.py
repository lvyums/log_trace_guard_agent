"""Tests for ai_core/llm_client.py"""
import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from log_guard.ai_core.llm_client import (
    LLMClient, EmbeddingClient, get_llm, get_embedding, reset_clients,
)


class TestLLMClient(unittest.TestCase):
    def setUp(self):
        reset_clients()

    @patch("log_guard.ai_core.llm_client.settings")
    def test_init(self, mock_settings):
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = "https://api.example.com/v1/"
        mock_settings.llm_model_name = "test-model"
        mock_settings.llm_temperature = 0.5
        mock_settings.llm_timeout = 10
        mock_settings.llm_max_tokens = 100

        client = LLMClient()
        self.assertEqual(client.api_key, "test-key")
        self.assertEqual(client.base_url, "https://api.example.com/v1")
        self.assertEqual(client.model, "test-model")

    @patch("log_guard.ai_core.llm_client.settings")
    def test_chat_no_api_key(self, mock_settings):
        mock_settings.llm_api_key = ""
        client = LLMClient()
        result = client.chat([{"role": "user", "content": "hi"}])
        self.assertFalse(result["success"])
        self.assertIn("未配置", result["error"])

    @patch("log_guard.ai_core.llm_client.requests")
    @patch("log_guard.ai_core.llm_client.settings")
    def test_chat_success(self, mock_settings, mock_requests):
        mock_settings.llm_api_key = "key"
        mock_settings.llm_base_url = "https://api.example.com"
        mock_settings.llm_model_name = "m"
        mock_settings.llm_temperature = 0.1
        mock_settings.llm_timeout = 30
        mock_settings.llm_max_tokens = 100

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "hello"}}]
        }
        mock_requests.post.return_value = mock_resp

        client = LLMClient()
        result = client.chat([{"role": "user", "content": "hi"}])
        self.assertTrue(result["success"])
        self.assertEqual(result["content"], "hello")

    @patch("log_guard.ai_core.llm_client.requests")
    @patch("log_guard.ai_core.llm_client.settings")
    def test_chat_timeout(self, mock_settings, mock_requests):
        mock_settings.llm_api_key = "key"
        mock_settings.llm_base_url = "https://api.example.com"
        mock_settings.llm_model_name = "m"
        mock_settings.llm_temperature = 0.1
        mock_settings.llm_timeout = 30
        mock_settings.llm_max_tokens = 100

        import requests as real_requests
        mock_requests.post.side_effect = real_requests.exceptions.Timeout()
        mock_requests.exceptions = real_requests.exceptions

        client = LLMClient()
        result = client.chat([{"role": "user", "content": "hi"}])
        self.assertFalse(result["success"])
        self.assertIn("超时", result["error"])

    @patch("log_guard.ai_core.llm_client.requests")
    @patch("log_guard.ai_core.llm_client.settings")
    def test_chat_json_success(self, mock_settings, mock_requests):
        mock_settings.llm_api_key = "key"
        mock_settings.llm_base_url = "https://api.example.com"
        mock_settings.llm_model_name = "m"
        mock_settings.llm_temperature = 0.1
        mock_settings.llm_timeout = 30
        mock_settings.llm_max_tokens = 100

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"key": "value"}'}}]
        }
        mock_requests.post.return_value = mock_resp

        client = LLMClient()
        result = client.chat_json([{"role": "user", "content": "hi"}])
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], {"key": "value"})

    @patch("log_guard.ai_core.llm_client.requests")
    @patch("log_guard.ai_core.llm_client.settings")
    def test_chat_json_invalid(self, mock_settings, mock_requests):
        mock_settings.llm_api_key = "key"
        mock_settings.llm_base_url = "https://api.example.com"
        mock_settings.llm_model_name = "m"
        mock_settings.llm_temperature = 0.1
        mock_settings.llm_timeout = 30
        mock_settings.llm_max_tokens = 100

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "not json"}}]
        }
        mock_requests.post.return_value = mock_resp

        client = LLMClient()
        result = client.chat_json([{"role": "user", "content": "hi"}])
        self.assertFalse(result["success"])

    @patch("log_guard.ai_core.llm_client.requests")
    @patch("log_guard.ai_core.llm_client.settings")
    def test_chat_json_extracts_from_code_block(self, mock_settings, mock_requests):
        mock_settings.llm_api_key = "key"
        mock_settings.llm_base_url = "https://api.example.com"
        mock_settings.llm_model_name = "m"
        mock_settings.llm_temperature = 0.1
        mock_settings.llm_timeout = 30
        mock_settings.llm_max_tokens = 100

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '```json\n{"a": 1}\n```'}}]
        }
        mock_requests.post.return_value = mock_resp

        client = LLMClient()
        result = client.chat_json([{"role": "user", "content": "hi"}])
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], {"a": 1})


class TestEmbeddingClient(unittest.TestCase):
    @patch("log_guard.ai_core.llm_client.settings")
    def test_init(self, mock_settings):
        mock_settings.llm_api_key = "key"
        mock_settings.llm_base_url = "https://api.example.com/v1/"
        mock_settings.embedding_model = "emb-model"
        client = EmbeddingClient()
        self.assertEqual(client.base_url, "https://api.example.com/v1")
        self.assertEqual(client.model, "emb-model")

    @patch("log_guard.ai_core.llm_client.settings")
    def test_embed_no_api_key(self, mock_settings):
        mock_settings.llm_api_key = ""
        client = EmbeddingClient()
        self.assertIsNone(client.embed("test"))

    @patch("log_guard.ai_core.llm_client.settings")
    def test_embed_batch_empty(self, mock_settings):
        mock_settings.llm_api_key = ""
        client = EmbeddingClient()
        self.assertEqual(client.embed_batch([]), [])

    @patch("log_guard.ai_core.llm_client.settings")
    def test_embed_batch_no_key(self, mock_settings):
        mock_settings.llm_api_key = ""
        client = EmbeddingClient()
        result = client.embed_batch(["a", "b"])
        self.assertEqual(result, [None, None])


class TestResetClients(unittest.TestCase):
    def test_reset(self):
        reset_clients()
        with patch("log_guard.ai_core.llm_client.settings") as mock_s:
            mock_s.llm_api_key = "k"
            mock_s.llm_base_url = "http://x"
            mock_s.llm_model_name = "m"
            mock_s.llm_temperature = 0.1
            mock_s.llm_timeout = 10
            mock_s.llm_max_tokens = 100
            mock_s.embedding_model = "e"
            a = get_llm()
        reset_clients()
        with patch("log_guard.ai_core.llm_client.settings") as mock_s:
            mock_s.llm_api_key = "k2"
            mock_s.llm_base_url = "http://x"
            mock_s.llm_model_name = "m"
            mock_s.llm_temperature = 0.1
            mock_s.llm_timeout = 10
            mock_s.llm_max_tokens = 100
            mock_s.embedding_model = "e"
            b = get_llm()
        self.assertIsNot(a, b)
        self.assertEqual(a.api_key, "k")
        self.assertEqual(b.api_key, "k2")


if __name__ == "__main__":
    unittest.main()
