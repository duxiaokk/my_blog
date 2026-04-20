from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.llm_service import chat_reply

router = APIRouter(prefix="/api", tags=["Chat"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    user_message: str


@router.post("/chat")
async def chat_with_avatar(request: ChatRequest):
    try:
        reply = await chat_reply(request.user_message)
    except RuntimeError as exc:
        logger.warning("chat unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception:
        logger.exception("chat request failed")
        raise HTTPException(status_code=500, detail="AI 分身暂时不可用，请稍后再试")
    return {"reply": reply}
