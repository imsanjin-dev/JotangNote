"""RabbitMQ publisher and Redis-backed status for asynchronous note operations."""
import json
import os
import uuid

import pika
import redis
from fastapi import HTTPException

from note_cache import redis_client

QUEUE_NAME = "jotang.note.operations"
TASK_TTL_SECONDS = 86400


def task_key(task_id: str) -> str:
    return f"jotang:task:{task_id}"


def save_status(task_id: str, state: dict) -> None:
    redis_client.setex(task_key(task_id), TASK_TTL_SECONDS, json.dumps(state, ensure_ascii=False))


def load_status(task_id: str) -> dict | None:
    raw = redis_client.get(task_key(task_id))
    return json.loads(raw) if raw is not None else None


def rabbit_parameters() -> pika.ConnectionParameters:
    return pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "127.0.0.1"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        credentials=pika.PlainCredentials(
            os.getenv("RABBITMQ_USER", "jotang"), os.environ["RABBITMQ_PASSWORD"]
        ),
        heartbeat=30,
        blocked_connection_timeout=5,
        socket_timeout=5,
        connection_attempts=1,
    )


def publish_note_task(operation: str, user_id: int, **fields) -> dict:
    task_id = uuid.uuid4().hex
    payload = {"task_id": task_id, "operation": operation, "user_id": user_id, **fields}
    status = {"task_id": task_id, "user_id": user_id, "status": "queued"}
    try:
        save_status(task_id, status)
    except (redis.RedisError, OSError):
        raise HTTPException(status_code=503, detail="任务状态服务暂不可用")

    connection = None
    try:
        connection = pika.BlockingConnection(rabbit_parameters())
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.confirm_delivery()
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            properties=pika.BasicProperties(
                delivery_mode=2, content_type="application/json", message_id=task_id
            ),
            mandatory=True,
        )
    except (pika.exceptions.AMQPError, OSError, KeyError, ValueError):
        try:
            redis_client.delete(task_key(task_id))
        except (redis.RedisError, OSError):
            pass
        raise HTTPException(status_code=503, detail="任务队列暂不可用，操作未确认入队")
    finally:
        if connection is not None and connection.is_open:
            connection.close()

    return {"task_id": task_id, "status": "queued", "message": "已接受任务，数据库尚未修改"}
