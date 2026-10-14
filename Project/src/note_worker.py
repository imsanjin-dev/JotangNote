"""Run separately: python Project/src/note_worker.py

One consumer, one unacknowledged operation at a time to preserve queue ordering
under normal operation. Redis holds user-facing task status, not the notes.
"""
import json
import logging
import time

import pika
import pymysql
import redis
from fastapi import HTTPException

from app import (
    NoteCreate,
    NoteUpdate,
    create_note_db,
    delete_note_db,
    get_connection,
    update_note_db,
)
from note_queue import QUEUE_NAME, rabbit_parameters, save_status, load_status

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("note-worker")


def lookup_user(user_id: int) -> dict | None:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()
    finally:
        connection.close()


def execute_task(task: dict) -> dict:
    """Recheck the user at execution time; synchronous handlers check note ownership."""
    user = lookup_user(task["user_id"])
    if user is None:
        raise HTTPException(status_code=401, detail="提交任务的用户已不存在")

    operation = task["operation"]
    if operation == "create":
        return create_note_db(
            NoteCreate(title=task["title"], content=task["content"]), user
        )
    if operation == "update":
        return update_note_db(
            task["note_id"],
            NoteUpdate(title=task["title"], content=task["content"]),
            user,
        )
    if operation == "delete":
        return delete_note_db(task["note_id"], user)
    raise ValueError("未知笔记操作")


def handle_delivery(channel, method, properties, body: bytes):
    """Always ACK after attempting the work; failures are visible via task status."""
    try:
        task = json.loads(body)
        task_id = task["task_id"]
        user_id = task["user_id"]
    except (ValueError, KeyError, TypeError):
        logger.error("Malformed queue message; discarding without executing")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    try:
        status = load_status(task_id)
        if status is not None and status.get("status") == "completed":
            logger.info("Skipping already completed task %s", task_id)
            return
        save_status(task_id, {"task_id": task_id, "user_id": user_id, "status": "processing"})
        result = execute_task(task)
        # A failed Redis status update must not turn a COMMITTED database write
        # into a failed task. Never retry a write solely because Redis went away.
        try:
            save_status(task_id, {
                "task_id": task_id, "user_id": user_id, "status": "completed", "result": result
            })
        except (redis.RedisError, OSError):
            logger.exception("DB committed but completion status could not be saved for %s", task_id)
        logger.info("Completed %s", task_id)
    except HTTPException as exc:
        logger.warning("Task %s rejected: %s", task_id, exc.detail)
        try:
            save_status(task_id, {
                "task_id": task_id, "user_id": user_id, "status": "failed",
                "http_status": exc.status_code, "error": exc.detail,
            })
        except (redis.RedisError, OSError):
            logger.exception("Cannot update failed task status %s", task_id)
    except Exception:
        logger.exception("Task %s failed", task_id)
        try:
            save_status(task_id, {
                "task_id": task_id, "user_id": user_id, "status": "failed",
                "error": "后台执行失败，请检查日志",
            })
        except (redis.RedisError, OSError):
            logger.exception("Cannot update failed task status %s", task_id)
    finally:
        channel.basic_ack(delivery_tag=method.delivery_tag)


def main():
    """Reconnect if RabbitMQ goes away; single worker avoids competing consumers."""
    while True:
        connection = None
        try:
            connection = pika.BlockingConnection(rabbit_parameters())
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=handle_delivery, auto_ack=False)
            logger.info("Consuming queue %s", QUEUE_NAME)
            channel.start_consuming()
        except (pika.exceptions.AMQPError, OSError):
            logger.exception("RabbitMQ disconnected; retrying in 5 seconds")
            time.sleep(5)
        finally:
            if connection is not None and connection.is_open:
                connection.close()


if __name__ == "__main__":
    main()
