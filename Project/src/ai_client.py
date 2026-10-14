"""Minimal OpenAI-compatible chat client for recruit advanced Part 1.

MiMo is the documented default, but provider URL/model/key can be configured.
No API request happens until POST /chat is called with an API key configured.
"""
import os

from fastapi import HTTPException
from openai import OpenAI, OpenAIError

DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"
DEFAULT_MODEL = "mimo-v2.6-flash"


def chat_once(message: str) -> str:
    """Send a single user message; multi-turn history belongs to Part 2."""
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="尚未配置 AI_API_KEY")

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("AI_BASE_URL", DEFAULT_BASE_URL),
        timeout=30.0,
        max_retries=0,
    )
    try:
        completion = client.chat.completions.create(
            model=os.getenv("AI_MODEL", DEFAULT_MODEL),
            messages=[
                {"role": "system", "content": "你是 JotangNote 的 AI 助手，请用简洁清楚的中文回答。"},
                {"role": "user", "content": message},
            ],
        )
    except OpenAIError:
        # Do not expose API keys, upstream errors or provider internals to clients.
        raise HTTPException(status_code=502, detail="AI 服务暂时不可用")

    if not completion.choices:
        raise HTTPException(status_code=502, detail="AI 服务没有返回有效回复")
    answer = completion.choices[0].message.content
    if not isinstance(answer, str) or not answer.strip():
        raise HTTPException(status_code=502, detail="AI 服务没有返回有效回复")
    return answer
