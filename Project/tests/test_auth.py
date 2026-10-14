import os
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import jwt
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import app as api

client = TestClient(api.app)

def db(row):
    c = MagicMock()
    cur = c.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = row
    cur.execute.return_value = 1
    cur.lastrowid = 21
    return c, cur

def auth():
    return {"Authorization": "Bearer " + api.create_access_token(7)}

class AuthTests(unittest.TestCase):
    def setUp(self):
        # These tests exercise the direct CRUD path, independent of the API's deployment mode.
        mode = patch.dict(os.environ, {"NOTE_WRITE_MODE": "sync"})
        mode.start()
        self.addCleanup(mode.stop)

    def test_login_issues_token(self):
        c, _ = db({"id": 7, "username": "alice",
                   "password_hash": api.password_hasher.hash("correct")})
        with patch.object(api, "get_connection", return_value=c):
            r = client.post("/login", json={"username": "alice", "password": "correct"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["expires_in"], 7200)
        self.assertEqual(jwt.decode(r.json()["access_token"],
                         os.environ["JWT_SECRET_KEY"], algorithms=["HS256"])["sub"], "7")
        self.assertNotIn("password_hash", r.json())
        c.close.assert_called_once()

    def test_login_rejects_wrong_password(self):
        c, _ = db({"id": 7, "username": "alice",
                   "password_hash": api.password_hasher.hash("correct")})
        with patch.object(api, "get_connection", return_value=c):
            r = client.post("/login", json={"username": "alice", "password": "wrong"})
        self.assertEqual(r.status_code, 401)

    def test_missing_invalid_expired_tokens(self):
        expired = jwt.encode({"sub": "7", "exp": datetime.now(UTC) -
                              timedelta(seconds=60)},
                             os.environ["JWT_SECRET_KEY"], algorithm="HS256")
        no_exp = jwt.encode({"sub": "7"}, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
        for token in (None, "wrong.token", expired, no_exp):
            headers = {} if token is None else {"Authorization": "Bearer " + token}
            with self.subTest(token=token is not None):
                with patch.object(api, "get_connection") as conn:
                    r = client.post("/notes", json={"title": "t", "content": "c"}, headers=headers)
                self.assertEqual(r.status_code, 401)
                conn.assert_not_called()

    def test_create_author_cannot_be_forged(self):
        user, _ = db({"id": 7, "username": "alice"})
        note, cur = db(None)
        with patch.object(api, "get_connection", side_effect=[user, note]):
            r = client.post("/notes", headers=auth(),
                            json={"title": "t", "content": "c", "author": "bob"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(cur.execute.call_args.args[1], ("t", "c", "alice"))
        note.commit.assert_called_once()

    def test_not_owner_cannot_edit_or_delete(self):
        for method in ("put", "delete"):
            user, _ = db({"id": 7, "username": "alice"})
            note, cur = db({"author": "bob"})
            kw = {"json": {"title": "t", "content": "c"}} if method == "put" else {}
            with patch.object(api, "get_connection", side_effect=[user, note]):
                r = getattr(client, method)("/notes/21", headers=auth(), **kw)
            self.assertEqual(r.status_code, 403)
            self.assertEqual(cur.execute.call_count, 1)
            note.commit.assert_not_called()
            note.close.assert_called_once()

    def test_owner_can_edit_and_delete(self):
        for method in ("put", "delete"):
            user, _ = db({"id": 7, "username": "alice"})
            note, cur = db({"author": "alice"})
            kw = {"json": {"title": "t", "content": "c"}} if method == "put" else {}
            with patch.object(api, "get_connection", side_effect=[user, note]):
                r = getattr(client, method)("/notes/21", headers=auth(), **kw)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(cur.execute.call_count, 2)
            self.assertEqual(cur.execute.call_args.args[1][-1], "alice")
            note.commit.assert_called_once()

    def test_deleted_user_cannot_use_old_token(self):
        user, _ = db(None)
        with patch.object(api, "get_connection", return_value=user):
            r = client.post("/notes", headers=auth(), json={"title": "t", "content": "c"})
        self.assertEqual(r.status_code, 401)

    def test_read_note_remains_public(self):
        note, _ = db({"id": 21, "author": "alice"})
        with patch.object(api, "get_connection", return_value=note):
            r = client.get("/notes/21")
        self.assertEqual(r.status_code, 200)

if __name__ == "__main__":
    unittest.main()
