"""Tests for the Redis cache-aside note lookup behavior (no live Redis needed)."""
import json
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import redis
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import app as api
import note_cache as cache

client = TestClient(api.app)


def mock_db(row):
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = row
    cursor.execute.return_value = 1
    return connection


def authorization():
    return {"Authorization": "Bearer " + api.create_access_token(7)}


class NoteCacheTests(unittest.TestCase):
    def test_cache_hit_skips_mysql(self):
        record = {"id": 42, "title": "Cached", "content": "hello"}
        with patch.object(cache, "redis_client") as r, patch.object(api, "get_connection") as db:
            r.get.return_value = json.dumps(record)
            response = client.get("/notes/42")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), record)
        r.get.assert_called_once_with("jotang:note:42")
        db.assert_not_called()

    def test_cache_miss_queries_mysql_and_sets_ttl(self):
        record = {"id": 42, "title": "New", "content": "hello",
                  "created_at": datetime(2026, 10, 14, 10, 0)}
        db = mock_db(record)
        with patch.object(cache, "redis_client") as r, patch.object(api, "get_connection", return_value=db):
            r.get.return_value = None
            response = client.get("/notes/42")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created_at"], "2026-10-14T10:00:00")
        key, ttl, payload = r.setex.call_args.args
        self.assertEqual((key, ttl), ("jotang:note:42", 300))
        self.assertEqual(json.loads(payload)["created_at"], "2026-10-14T10:00:00")
        db.close.assert_called_once()

    def test_missing_note_returns_404_without_caching(self):
        with patch.object(cache, "redis_client") as r, patch.object(
            api, "get_connection", return_value=mock_db(None)
        ):
            r.get.return_value = None
            response = client.get("/notes/404")
        self.assertEqual(response.status_code, 404)
        r.setex.assert_not_called()

    def test_redis_error_falls_back_to_mysql(self):
        with patch.object(cache, "redis_client") as r, patch.object(
            api, "get_connection", return_value=mock_db({"id": 42, "title": "DB"})
        ):
            r.get.side_effect = redis.ConnectionError("Redis down")
            r.setex.side_effect = redis.ConnectionError("Redis down")
            response = client.get("/notes/42")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "DB")

    def test_invalid_json_cache_treated_as_miss(self):
        with patch.object(cache, "redis_client") as r, patch.object(
            api, "get_connection", return_value=mock_db({"id": 42, "title": "DB"})
        ):
            r.get.return_value = "{bad"
            response = client.get("/notes/42")
        self.assertEqual(response.status_code, 200)
        r.setex.assert_called_once()

    def test_update_invalidates_after_database_commit(self):
        user = mock_db({"id": 7, "username": "alice"})
        note = mock_db({"author": "alice"})
        with patch.object(cache, "redis_client") as r, patch.object(
            api, "get_connection", side_effect=[user, note]
        ):
            response = client.put("/notes/42", headers=authorization(),
                                  json={"title": "Updated", "content": "new"})
        self.assertEqual(response.status_code, 200)
        note.commit.assert_called_once()
        r.delete.assert_called_once_with("jotang:note:42")

    def test_delete_invalidates_after_database_commit(self):
        user = mock_db({"id": 7, "username": "alice"})
        note = mock_db({"author": "alice"})
        with patch.object(cache, "redis_client") as r, patch.object(
            api, "get_connection", side_effect=[user, note]
        ):
            response = client.delete("/notes/42", headers=authorization())
        self.assertEqual(response.status_code, 200)
        note.commit.assert_called_once()
        r.delete.assert_called_once_with("jotang:note:42")

    def test_other_users_cannot_modify_or_invalidate(self):
        user = mock_db({"id": 7, "username": "alice"})
        note = mock_db({"author": "bob"})
        with patch.object(cache, "redis_client") as r, patch.object(
            api, "get_connection", side_effect=[user, note]
        ):
            response = client.delete("/notes/42", headers=authorization())
        self.assertEqual(response.status_code, 403)
        r.delete.assert_not_called()
        note.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
