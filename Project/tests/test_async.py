"""Small tests for the async handoff and worker; live broker checks are separate."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import redis
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import app as api
import note_queue as queue
import note_worker as worker


class AsyncNoteTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        api.app.dependency_overrides[api.get_current_user] = lambda: {"id": 7, "username": "alice"}
        self.previous_mode = os.environ.get("NOTE_WRITE_MODE")
        os.environ["NOTE_WRITE_MODE"] = "async"

    def tearDown(self):
        api.app.dependency_overrides.clear()
        if self.previous_mode is None:
            os.environ.pop("NOTE_WRITE_MODE", None)
        else:
            os.environ["NOTE_WRITE_MODE"] = self.previous_mode

    def test_async_create_returns_202_without_mysql(self):
        with patch.object(api, "get_connection") as db, patch.object(
            queue, "publish_note_task", return_value={"task_id": "123", "status": "queued"}
        ) as publish:
            response = self.client.post("/notes", json={"title": "hello", "content": "world"})
        self.assertEqual(response.status_code, 202)
        db.assert_not_called()
        publish.assert_called_once_with("create", 7, title="hello", content="world")

    def test_async_update_and_delete_are_queued(self):
        with patch.object(api, "get_connection") as db, patch.object(
            queue, "publish_note_task", return_value={"task_id": "123", "status": "queued"}
        ) as publish:
            put = self.client.put("/notes/41", json={"title": "new", "content": "body"})
            delete = self.client.delete("/notes/41")
        self.assertEqual([put.status_code, delete.status_code], [202, 202])
        db.assert_not_called()
        self.assertEqual(publish.call_count, 2)
        self.assertEqual(publish.call_args_list[1].args, ("delete", 7))

    def test_task_status_ownership(self):
        task_id = "a" * 32
        state = {"task_id": task_id, "user_id": 7, "status": "queued"}
        with patch.object(queue, "load_status", return_value=state):
            response = self.client.get(f"/tasks/{task_id}")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("user_id", response.json())

        state["user_id"] = 8
        with patch.object(queue, "load_status", return_value=state):
            response = self.client.get(f"/tasks/{task_id}")
        self.assertEqual(response.status_code, 403)

    def test_publisher_confirmation_and_failure(self):
        fake = MagicMock()
        fake.is_open = True
        with patch.object(queue, "save_status") as save, patch.object(
            queue.pika, "BlockingConnection", return_value=fake
        ), patch.object(queue, "rabbit_parameters", return_value=MagicMock()):
            result = queue.publish_note_task("create", 7, title="x", content="y")
        self.assertEqual(result["status"], "queued")
        self.assertEqual(save.call_count, 1)
        self.assertTrue(fake.channel.return_value.basic_publish.call_args.kwargs["mandatory"])
        fake.channel.return_value.confirm_delivery.assert_called_once()

        with patch.object(queue, "save_status"), patch.object(
            queue.pika, "BlockingConnection", side_effect=OSError("down")
        ), patch.object(queue, "rabbit_parameters", return_value=MagicMock()), patch.object(
            queue.redis_client, "delete"
        ) as cleanup:
            with self.assertRaises(HTTPException) as caught:
                queue.publish_note_task("delete", 7, note_id=17)
        self.assertEqual(caught.exception.status_code, 503)
        cleanup.assert_called_once()

    def test_worker_dispatch_uses_current_user(self):
        with patch.object(worker, "lookup_user", return_value={"id": 7, "username": "alice"}), patch.object(
            worker, "create_note_db", return_value={"id": 123}
        ) as create:
            result = worker.execute_task({
                "user_id": 7, "operation": "create", "title": "a", "content": "b"
            })
        self.assertEqual(result, {"id": 123})
        self.assertEqual(create.call_args.args[0].title, "a")

    def test_worker_ack_once_for_already_completed(self):
        channel, method = MagicMock(), MagicMock(delivery_tag=9)
        payload = json.dumps({"task_id": "a" * 32, "user_id": 7}).encode()
        with patch.object(worker, "load_status", return_value={"status": "completed"}), patch.object(
            worker, "execute_task"
        ) as operation:
            worker.handle_delivery(channel, method, None, payload)
        channel.basic_ack.assert_called_once_with(delivery_tag=9)
        operation.assert_not_called()

    def test_redis_failure_after_db_commit_never_marks_task_failed(self):
        channel, method = MagicMock(), MagicMock(delivery_tag=9)
        payload = json.dumps({"task_id": "a" * 32, "user_id": 7}).encode()
        with patch.object(worker, "load_status", return_value={"status": "queued"}), patch.object(
            worker, "save_status", side_effect=[None, redis.RedisError("cache down")]
        ) as save, patch.object(worker, "execute_task", return_value={"id": 18}) as operation:
            worker.handle_delivery(channel, method, None, payload)
        operation.assert_called_once()
        self.assertEqual(save.call_count, 2)
        channel.basic_ack.assert_called_once_with(delivery_tag=9)


if __name__ == "__main__":
    unittest.main()


class AsyncFailureTests(unittest.TestCase):
    """Negative-path verification without touching existing MySQL notes."""

    def setUp(self):
        self.client = TestClient(api.app)
        api.app.dependency_overrides[api.get_current_user] = lambda: {"id": 7, "username": "alice"}

    def tearDown(self):
        api.app.dependency_overrides.clear()

    def test_invalid_and_missing_task_status(self):
        bad = self.client.get("/tasks/not-a-task-id")
        self.assertEqual(bad.status_code, 404)
        with patch.object(queue, "load_status", return_value=None):
            missing = self.client.get("/tasks/" + "b" * 32)
        self.assertEqual(missing.status_code, 404)

    def test_redis_failure_in_task_lookup_is_503(self):
        with patch.object(queue, "load_status", side_effect=redis.RedisError("not reachable")):
            result = self.client.get("/tasks/" + "b" * 32)
        self.assertEqual(result.status_code, 503)

    def test_worker_rejects_missing_user(self):
        with patch.object(worker, "lookup_user", return_value=None), patch.object(
            worker, "delete_note_db"
        ) as deleted:
            with self.assertRaises(HTTPException) as caught:
                worker.execute_task({"user_id": 7, "operation": "delete", "note_id": 41})
        self.assertEqual(caught.exception.status_code, 401)
        deleted.assert_not_called()

    def test_worker_records_denied_delete_and_acks(self):
        body = json.dumps({
            "task_id": "b" * 32, "user_id": 7, "operation": "delete", "note_id": 41
        }).encode()
        channel, method = MagicMock(), MagicMock(delivery_tag=5)
        with patch.object(worker, "load_status", return_value={"status": "queued"}), patch.object(
            worker, "save_status"
        ) as save, patch.object(
            worker, "lookup_user", return_value={"id": 7, "username": "alice"}
        ), patch.object(
            worker, "delete_note_db",
            side_effect=HTTPException(status_code=403, detail="只能删除自己的笔记")
        ):
            worker.handle_delivery(channel, method, None, body)
        self.assertEqual(save.call_count, 2)
        self.assertEqual(save.call_args.args[1]["status"], "failed")
        self.assertEqual(save.call_args.args[1]["http_status"], 403)
        channel.basic_ack.assert_called_once_with(delivery_tag=5)

    def test_worker_records_missing_note_and_acks(self):
        body = json.dumps({
            "task_id": "b" * 32, "user_id": 7, "operation": "delete", "note_id": 444
        }).encode()
        channel, method = MagicMock(), MagicMock(delivery_tag=6)
        with patch.object(worker, "load_status", return_value={"status": "queued"}), patch.object(
            worker, "save_status"
        ) as save, patch.object(
            worker, "execute_task",
            side_effect=HTTPException(status_code=404, detail="笔记不存在"),
        ):
            worker.handle_delivery(channel, method, None, body)
        self.assertEqual(save.call_args.args[1]["http_status"], 404)
        channel.basic_ack.assert_called_once_with(delivery_tag=6)

    def test_invalid_message_is_acked_without_database_write(self):
        channel, method = MagicMock(), MagicMock(delivery_tag=17)
        with patch.object(worker, "execute_task") as execute:
            worker.handle_delivery(channel, method, None, b"{invalid json")
        execute.assert_not_called()
        channel.basic_ack.assert_called_once_with(delivery_tag=17)
