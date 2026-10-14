"""Advanced Part 2/3 and frontend tests. All model/network responses are mocked."""
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ai_client
import app as api
from chat_session import clear_sessions, get_history, get_session, MAX_TURNS

client = TestClient(api.app)


def answer(content=None, tool_calls=None):
    return SimpleNamespace(choices=[
        SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=tool_calls))
    ])


def tool_call(id="call_1", name="get_note_by_id", arguments='{"note_id":5}'):
    return SimpleNamespace(id=id, function=SimpleNamespace(name=name, arguments=arguments))


class AdvancedChatTests(unittest.TestCase):
    def setUp(self):
        clear_sessions()
        api.app.dependency_overrides[api.get_current_user] = lambda: {"id": 8, "username": "alice"}
        self.env = patch.dict(os.environ, {"AI_API_KEY": "unit-test-only"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        api.app.dependency_overrides.clear()
        clear_sessions()

    def test_two_turns_reuse_history(self):
        fake = MagicMock()
        fake.chat.completions.create.side_effect = [answer("第一轮回答"), answer("第二轮回答")]
        with patch.object(ai_client, "OpenAI", return_value=fake):
            first = client.post("/chat", json={"message": "第一轮"}).json()
            second = client.post("/chat", json={
                "message": "第二轮", "conversation_id": first["conversation_id"]
            }).json()
        self.assertEqual(second["reply"], "第二轮回答")
        self.assertEqual(second["conversation_id"], first["conversation_id"])
        sent = fake.chat.completions.create.call_args_list[1].kwargs["messages"]
        self.assertEqual([m["role"] for m in sent], ["system", "user", "assistant", "user"])
        self.assertEqual(sent[1]["content"], "第一轮")
        self.assertEqual(sent[2]["content"], "第一轮回答")

    def test_users_cannot_read_other_sessions(self):
        fake = MagicMock()
        fake.chat.completions.create.return_value = answer("你好")
        with patch.object(ai_client, "OpenAI", return_value=fake):
            first = client.post("/chat", json={"message": "用户 A"}).json()
            api.app.dependency_overrides[api.get_current_user] = lambda: {"id": 9, "username": "bob"}
            forbidden = client.post("/chat", json={
                "message": "盗用", "conversation_id": first["conversation_id"]
            })
        self.assertEqual(forbidden.status_code, 404)
        self.assertEqual(fake.chat.completions.create.call_count, 1)

    def test_unknown_or_invalid_session(self):
        invalid = client.post("/chat", json={"message": "你好", "conversation_id": "wrong"})
        unknown = client.post("/chat", json={"message": "你好", "conversation_id": "a" * 32})
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(unknown.status_code, 404)

    def test_note_tool_followup_is_private_and_saved_in_history(self):
        fake = MagicMock()
        fake.chat.completions.create.side_effect = [
            answer(None, [tool_call()]),
            answer("这是笔记 5 的摘要"),
            answer("刚才总结的是笔记 5"),
        ]
        with patch.object(ai_client, "OpenAI", return_value=fake), patch.object(
            api, "get_note", return_value={"id": 5, "title": "例子", "content": "真实正文"}
        ) as reader:
            first = client.post("/chat", json={"message": "总结笔记 5"})
            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.json()["reply"], "这是笔记 5 的摘要")
            second = client.post("/chat", json={
                "message": "刚才总结了哪篇？",
                "conversation_id": first.json()["conversation_id"],
            })
        reader.assert_called_once_with(5)
        self.assertEqual(second.status_code, 200)
        args = fake.chat.completions.create.call_args_list
        call_one = args[0].kwargs
        self.assertEqual(call_one["tools"][0]["function"]["name"], "get_note_by_id")
        followup = args[1].kwargs["messages"]
        self.assertEqual(followup[-2]["role"], "assistant")
        self.assertEqual(followup[-1]["role"], "tool")
        self.assertEqual(followup[-1]["tool_call_id"], "call_1")
        self.assertEqual(json.loads(followup[-1]["content"])["note"]["content"], "真实正文")
        repeat = args[2].kwargs["messages"]
        self.assertEqual([m["role"] for m in repeat[:6]], [
            "system", "user", "assistant", "tool", "assistant", "user"
        ])

    def test_bad_tool_arguments_are_not_executed(self):
        fake = MagicMock()
        fake.chat.completions.create.side_effect = [
            answer(None, [tool_call(arguments='{"note_id":true}')]), answer("无效 ID")
        ]
        with patch.object(ai_client, "OpenAI", return_value=fake), patch.object(api, "get_note") as reader:
            response = client.post("/chat", json={"message": "查笔记"})
        self.assertEqual(response.status_code, 200)
        reader.assert_not_called()
        self.assertIn("正整数", fake.chat.completions.create.call_args_list[1].kwargs["messages"][-1]["content"])

    def test_unknown_tool_does_not_execute_note_lookup(self):
        fake = MagicMock()
        fake.chat.completions.create.side_effect = [
            answer(None, [tool_call(name="delete_note")]), answer("不能操作")
        ]
        with patch.object(ai_client, "OpenAI", return_value=fake), patch.object(api, "get_note") as reader:
            result = client.post("/chat", json={"message": "删除笔记"})
        self.assertEqual(result.status_code, 200)
        reader.assert_not_called()

    def test_missing_note_returns_tool_error_to_ai(self):
        from fastapi import HTTPException
        fake = MagicMock()
        fake.chat.completions.create.side_effect = [
            answer(None, [tool_call()]), answer("笔记不存在")
        ]
        with patch.object(ai_client, "OpenAI", return_value=fake), patch.object(
            api, "get_note", side_effect=HTTPException(status_code=404)
        ):
            result = client.post("/chat", json={"message": "查询不存在的笔记"})
        self.assertEqual(result.status_code, 200)
        self.assertIn("笔记不存在", fake.chat.completions.create.call_args_list[1].kwargs["messages"][-1]["content"])

    def test_provider_failure_keeps_history_clean(self):
        from openai import OpenAIError
        fake = MagicMock()
        fake.chat.completions.create.side_effect = [answer("成功"), OpenAIError("upstream broken")]
        with patch.object(ai_client, "OpenAI", return_value=fake):
            first = client.post("/chat", json={"message": "可以"}).json()
            second = client.post("/chat", json={
                "message": "失败", "conversation_id": first["conversation_id"]
            })
        self.assertEqual(second.status_code, 502)
        _, session = get_session(8, first["conversation_id"])
        self.assertEqual(len(session.turns), 1)
        self.assertEqual(len(get_history(session)), 2)

    def test_turns_are_trimmed_atomically(self):
        fake = MagicMock()
        fake.chat.completions.create.return_value = answer("好的")
        with patch.object(ai_client, "OpenAI", return_value=fake):
            conversation_id = None
            for index in range(MAX_TURNS + 2):
                payload = {"message": f"第 {index} 轮"}
                if conversation_id:

                    payload["conversation_id"] = conversation_id
                response = client.post("/chat", json=payload)
                self.assertEqual(response.status_code, 200)
                conversation_id = response.json()["conversation_id"]
        _, session = get_session(8, conversation_id)
        self.assertEqual(len(session.turns), MAX_TURNS)
        self.assertEqual(session.turns[0][0]["content"], "第 2 轮")

    def test_tool_recursion_limit(self):
        fake = MagicMock()
        fake.chat.completions.create.return_value = answer(None, [tool_call()])
        with patch.object(ai_client, "OpenAI", return_value=fake), patch.object(api, "get_note", return_value={"id": 5}):
            result = client.post("/chat", json={"message": "反复查询"})
        self.assertEqual(result.status_code, 502)
        self.assertLessEqual(fake.chat.completions.create.call_count, ai_client.MAX_TOOL_ROUNDS + 1)

    def test_frontend_exists_with_controls(self):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        for label in ("JotangNote", "id=\"loginBtn\"", "id=\"createBtn\"", "id=\"sendBtn\""):
            self.assertIn(label, response.text)


if __name__ == "__main__":
    unittest.main()
