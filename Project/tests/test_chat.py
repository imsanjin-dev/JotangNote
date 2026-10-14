"""Advanced Part 1 chat endpoint tests; no external API calls."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from openai import OpenAIError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import app as api
import ai_client
from chat_session import clear_sessions

client = TestClient(api.app)


class ChatTests(unittest.TestCase):
    def setUp(self):
        clear_sessions()
        api.app.dependency_overrides[api.get_current_user] = lambda: {
            "id": 9, "username": "student"
        }

    def tearDown(self):
        clear_sessions()
        api.app.dependency_overrides.clear()

    def test_missing_key_returns_503(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AI_API_KEY", None)
            response = client.post("/chat", json={"message": "你好"})
        self.assertEqual(response.status_code, 503)

    def test_successful_provider_answer(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="你好，我是笔记助手", tool_calls=None))
        ]
        with patch.dict(os.environ, {"AI_API_KEY": "test-not-real", "AI_MODEL": "demo"}), patch.object(
            ai_client, "OpenAI", return_value=mock_client
        ) as constructor:
            response = client.post("/chat", json={"message": "你好"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "你好，我是笔记助手")
        self.assertEqual(mock_client.chat.completions.create.call_args.kwargs["model"], "demo")
        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        self.assertEqual(messages[-1], {"role": "user", "content": "你好"})
        self.assertEqual(constructor.call_args.kwargs["api_key"], "test-not-real")

    def test_provider_failure_returns_502(self):
        fake = MagicMock()
        fake.chat.completions.create.side_effect = OpenAIError("unavailable")
        with patch.dict(os.environ, {"AI_API_KEY": "test-not-real"}), patch.object(
            ai_client, "OpenAI", return_value=fake
        ):
            response = client.post("/chat", json={"message": "你好"})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("unavailable", response.text)

    def test_no_answer_returns_502(self):
        fake = MagicMock()
        fake.chat.completions.create.return_value.choices = []
        with patch.dict(os.environ, {"AI_API_KEY": "test-not-real"}), patch.object(
            ai_client, "OpenAI", return_value=fake
        ):
            response = client.post("/chat", json={"message": "你好"})
        self.assertEqual(response.status_code, 502)

    def test_input_validation(self):
        self.assertEqual(client.post("/chat", json={"message": ""}).status_code, 422)
        self.assertEqual(client.post("/chat", json={"message": " "}).status_code, 422)
        self.assertEqual(client.post("/chat", json={"message": "x" * 4001}).status_code, 422)

    def test_authentication_required(self):
        api.app.dependency_overrides.clear()
        response = client.post("/chat", json={"message": "你好"})
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
