from __future__ import annotations

import asyncio
import logging
from functools import lru_cache

from core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are the AI persona for Ado_Jk. "
    "Keep replies clear, technical, and concise."
)


@lru_cache(maxsize=1)
def _get_client():
    try:
        from zhipuai import ZhipuAI
    except Exception as exc:  # pragma: no cover - optional dependency
        logger.warning("zhipuai import failed: %s", exc)
        return None

    if not settings.zhipuai_api_key:
        return None
    return ZhipuAI(api_key=settings.zhipuai_api_key)


async def chat_reply(user_message: str) -> str:
    client = _get_client()
    if not client:
        raise RuntimeError("AI assistant is unavailable (missing zhipuai dependency or API key)")

    def _call_api():
        return client.chat.completions.create(
            model="glm-4.5-air",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.6,
            max_tokens=250,
        )

    response = await asyncio.to_thread(_call_api)
    return response.choices[0].message.content
