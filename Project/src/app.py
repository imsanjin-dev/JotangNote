import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import jwt
import pymysql
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel
from pwdlib import PasswordHash
from note_cache import cache_note, get_cached_note, invalidate_note_cache

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
password_hasher = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)
ACCESS_TOKEN_EXPIRE_MINUTES = 120
JWT_ALGORITHM = "HS256"

class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str

class NoteCreate(BaseModel):
    title: str
    content: str


class NoteUpdate(BaseModel):
    title: str
    content: str


def get_connection():
    return pymysql.connect(
        host="127.0.0.1",
        user="jotang_app",
        password=os.environ["DB_PASSWORD"],
        database="jotang_note",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


app = FastAPI()


def create_access_token(user_id: int) -> str:
    expire_at = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire_at}
    return jwt.encode(payload, os.environ["JWT_SECRET_KEY"], algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
):
    auth_error = HTTPException(
        status_code=401,
        detail="登录状态无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise auth_error

    try:
        payload = jwt.decode(
            credentials.credentials,
            os.environ["JWT_SECRET_KEY"],
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        user_id = payload.get("sub")
        if not isinstance(user_id, str) or not user_id.isdigit() or int(user_id) < 1:
            raise auth_error
    except InvalidTokenError:
        raise auth_error

    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, username FROM users WHERE id = %s", (int(user_id),))
            current_user = cursor.fetchone()
    except pymysql.MySQLError:
        raise HTTPException(status_code=500, detail="数据库查询失败")
    finally:
        if connection is not None:
            connection.close()

    if current_user is None:
        raise auth_error
    return current_user


@app.get("/hello", response_class=PlainTextResponse)
def hello():
    return "Hello World From Web Application!"


@app.get("/notes/{note_id}")
def get_note(note_id: int):
    cached_note = get_cached_note(note_id)
    if cached_note is not None:
        return cached_note

    connection = None

    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM notes WHERE id = %s"
            cursor.execute(sql, (note_id,))
            note = cursor.fetchone()

    except pymysql.MySQLError:
        raise HTTPException(status_code=500, detail="数据库查询失败")
    finally:
        if connection is not None:
            connection.close()

    if note is None:
        raise HTTPException(status_code=404, detail="笔记不存在")

    cache_note(note_id, note)
    return note


@app.post("/notes", status_code=201)
def create_note(note: NoteCreate, current_user: Annotated[dict, Depends(get_current_user)]):
    connection = None

    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            sql = "INSERT INTO notes (title, content, author) VALUES (%s, %s, %s);"
            affected_rows = cursor.execute(sql, (note.title, note.content, current_user["username"]))
            if affected_rows != 1:
                connection.rollback()
                raise HTTPException(status_code=500, detail="笔记插入失败")
            new_id = cursor.lastrowid
        connection.commit()
        return {"id": new_id, "message": "创建成功"}
    except pymysql.MySQLError:
        if connection is not None:
            connection.rollback()
        raise HTTPException(status_code=500, detail="笔记插入失败")
    finally:
        if connection is not None:
            connection.close()

@app.post("/register",status_code=201)
def create_user(user: UserRegister):
    connection = None
    try:
        connection=get_connection()
        hashed = password_hasher.hash(user.password)
        with connection.cursor() as cursor:
            sql = "INSERT INTO users (username, password_hash) VALUES (%s, %s);"
            affected_rows=cursor.execute(sql,(user.username,hashed))
            if affected_rows != 1:
                connection.rollback()
                raise HTTPException(status_code=500, detail="用户创建失败")
            new_id=cursor.lastrowid
        connection.commit()
        return {"id": new_id, "message": "创建成功"}

    except pymysql.IntegrityError as error:
        if connection is not None:
            connection.rollback()

        if error.args[0] == 1062:
            raise HTTPException(
                status_code=409,
                detail="用户名已存在"
            )
        raise HTTPException(
            status_code=500,
            detail="用户创建失败"
        )
    except pymysql.MySQLError:
            if connection is not None:
                connection.rollback()
            raise HTTPException(status_code=500, detail="用户创建失败")
    finally:
        if connection is not None:
            connection.close()


@app.post("/login")
def login_user(user: UserLogin):
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            sql = "SELECT id, username, password_hash FROM users WHERE username = %s"
            cursor.execute(sql, (user.username,))
            existing_user = cursor.fetchone()
    except pymysql.MySQLError:
        raise HTTPException(status_code=500, detail="数据库查询失败")
    finally:
        if connection is not None:
            connection.close()

    if existing_user is None or not password_hasher.verify(user.password, existing_user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    access_token = create_access_token(existing_user["id"])
    return {
        "id": existing_user["id"],
        "username": existing_user["username"],
        "message": "登录成功",
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@app.put("/notes/{note_id}")
def update_note(note_id: int, note: NoteUpdate, current_user: Annotated[dict, Depends(get_current_user)]):
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM notes WHERE id = %s"
            cursor.execute(sql, (note_id,))
            existing_note = cursor.fetchone()
            if existing_note is None:
                raise HTTPException(status_code=404, detail=f"笔记 ID {note_id} 不存在")
            if existing_note["author"] != current_user["username"]:
                raise HTTPException(status_code=403, detail="只能修改自己的笔记")
            sql = "UPDATE notes SET title = %s, content = %s WHERE id = %s AND author = %s"
            affected_rows = cursor.execute(
                sql, (note.title, note.content, note_id, current_user["username"])
            )
            if affected_rows not in (0, 1):
                connection.rollback()
                raise HTTPException(status_code=500, detail="数据更新异常")
        connection.commit()
        invalidate_note_cache(note_id)
        return {"id": note_id, "message": "修改成功"}
    except pymysql.MySQLError:
        if connection is not None:
            connection.rollback()
        raise HTTPException(status_code=500, detail="数据更新异常")
    finally:
        if connection is not None:
            connection.close()

@app.delete("/notes/{note_id}")
def delete_note(note_id: int, current_user: Annotated[dict, Depends(get_current_user)]):
    connection=None
    try:
        connection=get_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT author FROM notes WHERE id = %s", (note_id,))
            existing_note = cursor.fetchone()
            if existing_note is None:
                raise HTTPException(status_code=404, detail=f"笔记 ID {note_id} 不存在")
            if existing_note["author"] != current_user["username"]:
                raise HTTPException(status_code=403, detail="只能删除自己的笔记")
            sql = "DELETE FROM notes WHERE id = %s AND author = %s"
            affected_rows = cursor.execute(sql, (note_id, current_user["username"]))
            if affected_rows != 1:
                connection.rollback()
                raise HTTPException(status_code=404, detail=f"笔记 ID {note_id} 不存在")
        connection.commit()
        invalidate_note_cache(note_id)
        return {"id": note_id, "message": "删除成功"}
    except pymysql.MySQLError:
        if connection is not None:
            connection.rollback()
        raise HTTPException(status_code=500, detail="数据库查询失败")
    finally:
        if connection is not None:
            connection.close()
