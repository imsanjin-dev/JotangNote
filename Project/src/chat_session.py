"""In-memory, per-user conversation history for JotangNote advanced Part 2.

Each committed turn contains the user question, any hidden tool exchange and the
final assistant reply. Trimming by *turn*, not message, keeps tool results paired
with their calls. The store intentionally does not survive a server restart.
"""
from dataclasses import dataclass, field
from threading import Lock, RLock
from time import monotonic
from uuid import uuid4

from fastapi import HTTPException

SESSION_TTL_SECONDS = 1800
MAX_SESSIONS = 200
MAX_TURNS = 10


@dataclass
class ChatSession:
    owner_id: int
    turns: list[list[dict]] = field(default_factory=list)
    accessed_at: float = field(default_factory=monotonic)
    lock: RLock = field(default_factory=RLock)


_sessions: dict[str, ChatSession] = {}
_sessions_lock = Lock()


def get_session(owner_id: int, conversation_id: str | None) -> tuple[str, ChatSession]:
    """Return only the caller's session, or create a fresh random ID."""
    with _sessions_lock:
        now = monotonic()
        for key, entry in list(_sessions.items()):
            if now - entry.accessed_at >= SESSION_TTL_SECONDS:
                del _sessions[key]

        if conversation_id is not None:
            session = _sessions.get(conversation_id)
            if session is None or session.owner_id != owner_id:
                # Do not disclose whether this ID belongs to someone else.
                raise HTTPException(status_code=404, detail="会话不存在或已过期")
            session.accessed_at = now
            return conversation_id, session

        while len(_sessions) >= MAX_SESSIONS:
            oldest = min(_sessions, key=lambda key: _sessions[key].accessed_at)
            del _sessions[oldest]
        new_id = uuid4().hex
        session = ChatSession(owner_id=owner_id)
        _sessions[new_id] = session
        return new_id, session


def get_history(session: ChatSession) -> list[dict]:
    return [message for turn in session.turns for message in turn]


def commit_turn(session: ChatSession, messages: list[dict]) -> None:
    """Only save a complete successful question→answer exchange."""
    session.turns.append(messages)
    session.turns = session.turns[-MAX_TURNS:]
    session.accessed_at = monotonic()


def clear_sessions() -> None:
    """Test fixture helper; never exposed as a public unauthenticated API."""
    with _sessions_lock:
        _sessions.clear()
