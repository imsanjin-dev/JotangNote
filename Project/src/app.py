import os

import pymysql
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from pydantic import BaseModel


class NoteCreate(BaseModel):
    title: str
    content: str
    author: str


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


@app.get("/hello", response_class=PlainTextResponse)
def hello():
    return "Hello World From Web Application!"


@app.get("/notes/{note_id}")
def get_note(note_id: int):
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

    return note


@app.post("/notes", status_code=201)
def create_note(note: NoteCreate):
    connection = None

    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            sql = "INSERT INTO notes (title, content, author) VALUES (%s, %s, %s);"
            affected_rows = cursor.execute(sql, (note.title, note.content, note.author))
            if affected_rows != 1:
                connection.rollback()
                raise HTTPException(status_code=500, detail="笔记插入失败")

            new_id = cursor.lastrowid
        connection.commit()
        return {"id": new_id, "message": "创建成功"}
    except pymysql.MySQLError:
        if connection is not None:
            connection.rollback()
        raise HTTPException(status_code=500, detail="数据库查询失败")
    finally:
        if connection is not None:
            connection.close()


@app.put("/notes/{note_id}")
def update_note(note_id: int, note: NoteUpdate):
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM notes WHERE id = %s"
            cursor.execute(sql, (note_id,))
            existing_note = cursor.fetchone()
            if existing_note is None:
                raise HTTPException(status_code=404, detail=f"笔记 ID {note_id} 不存在")
            sql = "UPDATE notes SET title = %s, content = %s WHERE id = %s"
            affected_rows = cursor.execute(sql, (note.title, note.content, note_id))
            if affected_rows not in (0, 1):
                connection.rollback()
                raise HTTPException(status_code=500, detail="数据更新异常")
        connection.commit()
        return {"id": note_id, "message": "修改成功"}
    except pymysql.MySQLError:
        if connection is not None:
            connection.rollback()
        raise HTTPException(status_code=500, detail="数据库查询失败")
    finally:
        if connection is not None:
            connection.close()

@app.delete("/notes/{note_id}")
def delete_note(note_id: int):
    connection=None
    try:
        connection=get_connection()
        with connection.cursor() as cursor:
            sql="DELETE FROM notes WHERE id = %s"
            affected_rows=cursor.execute(sql,(note_id,))
            if affected_rows != 1:
                connection.rollback()
                raise HTTPException(status_code=404, detail=f"笔记 ID {note_id} 不存在")
        connection.commit()
        return {"id": note_id, "message": "删除成功"}
    except pymysql.MySQLError:
        if connection is not None:
            connection.rollback()
        raise HTTPException(status_code=500, detail="数据库查询失败")
    finally:
        if connection is not None:
            connection.close()
