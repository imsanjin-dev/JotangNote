"""Redis cache helpers for the public note lookup endpoint."""
import json
import os

import redis
from fastapi.encoders import jsonable_encoder
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

CACHE_TTL_SECONDS = 300
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
    decode_responses=True,
    socket_connect_timeout=0.5,
    socket_timeout=0.5,
)


def note_cache_key(note_id: int) -> str:
    return f"jotang:note:{note_id}"


def get_cached_note(note_id: int) -> dict | None:
    """A missing/unavailable cache is a miss; MySQL remains the source of truth."""
    try:
        raw = redis_client.get(note_cache_key(note_id))
    except (redis.RedisError, OSError):
        return None

    if raw is None:
        return None
    try:
        note = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return note if isinstance(note, dict) else None


def cache_note(note_id: int, note: dict) -> None:
    try:
        redis_client.setex(
            note_cache_key(note_id),
            CACHE_TTL_SECONDS,
            json.dumps(jsonable_encoder(note), ensure_ascii=False),
        )
    except (redis.RedisError, OSError):
        # Cache outages must not turn a successful database read into a 500.
        pass


def invalidate_note_cache(note_id: int) -> None:
    try:
        redis_client.delete(note_cache_key(note_id))
    except (redis.RedisError, OSError):
        # Redis failures cannot roll back an already committed MySQL change.
        pass
