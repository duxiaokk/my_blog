from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import defaultdict
from typing import Dict, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models
import security
from database import get_db
from web_deps import (
    comment_rate_limiter,
    get_client_ip,
    get_optional_user,
    is_admin,
    verify_csrf,
)


router = APIRouter()


class CommentCreateRequest(BaseModel):
    content: str
    parent_id: Optional[int] = None


class CommentUpdateRequest(BaseModel):
    content: str


def _comment_to_dict(c: models.Comment, username: str, liked_by_me: bool = False) -> dict:
    return {
        "id": c.id,
        "article_id": c.article_id,
        "user_id": c.user_id,
        "username": username,
        "parent_id": c.parent_id,
        "content": c.content,
        "like_count": int(c.like_count or 0),
        "liked_by_me": bool(liked_by_me),
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


class _CommentBus:
    def __init__(self) -> None:
        self._subs: Dict[int, Set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, post_id: int) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subs[int(post_id)].add(q)
        return q

    def unsubscribe(self, post_id: int, q: asyncio.Queue) -> None:
        self._subs[int(post_id)].discard(q)

    def publish(self, post_id: int, event: dict) -> None:
        subs = list(self._subs.get(int(post_id), set()))
        for q in subs:
            try:
                q.put_nowait(event)
            except Exception:
                pass


comment_bus = _CommentBus()


@router.get("/posts/{post_id}/comments")
def list_comments(
    post_id: int,
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
    user: Optional[str] = Depends(get_optional_user),
):
    page = max(1, int(page))
    page_size = max(1, min(50, int(page_size)))

    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")

    q = (
        db.query(models.Comment, models.User.username)
        .join(models.User, models.User.id == models.Comment.user_id)
        .filter(models.Comment.article_id == post_id, models.Comment.status == "active")
        .order_by(models.Comment.created_at.desc(), models.Comment.id.desc())
    )
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()

    liked_ids: Set[int] = set()
    if user and rows:
        current = db.query(models.User).filter(models.User.username == user).first()
        if current:
            comment_ids = [int(c.id) for c, _ in rows]
            liked_rows = (
                db.query(models.CommentLike.comment_id)
                .filter(
                    models.CommentLike.user_id == current.id,
                    models.CommentLike.comment_id.in_(comment_ids),
                )
                .all()
            )
            liked_ids = {int(x[0]) for x in liked_rows}

    items = [_comment_to_dict(c, username, liked_by_me=(int(c.id) in liked_ids)) for c, username in rows]
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/posts/{post_id}/comments/stream")
async def comment_stream(post_id: int, request: Request):
    async def gen():
        q = comment_bus.subscribe(post_id)
        try:
            yield "event: ready\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15.0)
                    payload = json.dumps(ev, ensure_ascii=False)
                    yield f"event: comment\ndata: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield "event: ping\ndata: {}\n\n"
        finally:
            comment_bus.unsubscribe(post_id, q)

    return StreamingResponse(gen(), media_type="text/event-stream")

@router.post("/posts/{post_id}/comments")
async def create_comment(
    post_id: int,
    request: Request,
    body: CommentCreateRequest,
    db: Session = Depends(get_db),
    user: str = Depends(security.get_current_user_from_cookie),
):
    if not comment_rate_limiter.allow(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="操作过于频繁，请稍后再试")
    verify_csrf(request)

    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")

    current = db.query(models.User).filter(models.User.username == user).first()
    if not current:
        raise HTTPException(status_code=401, detail="未登录")

    content = body.content.strip()
    
    if not content:
        raise HTTPException(status_code=400, detail="评论内容不能为空")
    if len(content) > 2000:
        raise HTTPException(status_code=400, detail="评论内容过长")

    if body.parent_id is not None:
        parent = (
            db.query(models.Comment)
            .filter(models.Comment.id == body.parent_id, models.Comment.article_id == post_id)
            .first()
        )
        if not parent:
            raise HTTPException(status_code=400, detail="回复的评论不存在")
    comment = models.Comment(
        article_id=post_id,
        user_id=current.id,
        parent_id=body.parent_id,
        content=content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    payload = _comment_to_dict(comment, user)
    comment_bus.publish(post_id, {"type": "created", "comment": payload})
    return payload


@router.put("/comments/{comment_id}")
async def update_comment(
    comment_id: int,
    request: Request,
    body: CommentUpdateRequest,
    db: Session = Depends(get_db),
    user: str = Depends(security.get_current_user_from_cookie),
):
    if not comment_rate_limiter.allow(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="操作过于频繁，请稍后再试")
    verify_csrf(request)

    comment = (
        db.query(models.Comment)
        .filter(models.Comment.id == comment_id, models.Comment.status == "active")
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    current = db.query(models.User).filter(models.User.username == user).first()
    if not current:
        raise HTTPException(status_code=401, detail="未登录")
    if comment.user_id != current.id:
        raise HTTPException(status_code=403, detail="只能修改自己的评论")

    content = body.content.strip()

    if not content:
        raise HTTPException(status_code=400, detail="评论内容不能为空")
    if len(content) > 2000:
        raise HTTPException(status_code=400, detail="评论内容过长")

    comment.content = content
    db.commit()
    db.refresh(comment)

    payload = _comment_to_dict(comment, user)
    comment_bus.publish(comment.article_id, {"type": "updated", "comment": payload})
    return payload


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: str = Depends(security.get_current_user_from_cookie),
):
    if not comment_rate_limiter.allow(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="操作过于频繁，请稍后再试")
    verify_csrf(request)

    comment = (
        db.query(models.Comment)
        .filter(models.Comment.id == comment_id, models.Comment.status == "active")
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    current = db.query(models.User).filter(models.User.username == user).first()
    if not current:
        raise HTTPException(status_code=401, detail="未登录")
    if comment.user_id != current.id and not is_admin(user):
        raise HTTPException(status_code=403, detail="只能删除自己的评论")

    comment.status = "deleted"
    db.commit()
    comment_bus.publish(comment.article_id, {"type": "deleted", "comment_id": comment_id})
    return {"message": "已删除"}


@router.post("/comments/{comment_id}/like")
async def like_comment(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    if not comment_rate_limiter.allow(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="操作过于频繁，请稍后再试")
    verify_csrf(request)

    comment = (
        db.query(models.Comment)
        .filter(models.Comment.id == comment_id, models.Comment.status == "active")
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    current_username = get_optional_user(request)
    if not current_username:
        comment.like_count = int(comment.like_count or 0) + 1
        db.commit()
        db.refresh(comment)
        comment_bus.publish(comment.article_id, {"type": "liked", "comment_id": comment_id, "like_count": int(comment.like_count or 0)})
        return {"like_count": int(comment.like_count or 0), "liked": False}

    current = db.query(models.User).filter(models.User.username == current_username).first()
    if not current:
        comment.like_count = int(comment.like_count or 0) + 1
        db.commit()
        db.refresh(comment)
        comment_bus.publish(comment.article_id, {"type": "liked", "comment_id": comment_id, "like_count": int(comment.like_count or 0)})
        return {"like_count": int(comment.like_count or 0), "liked": False}

    existing = (
        db.query(models.CommentLike)
        .filter(models.CommentLike.user_id == current.id, models.CommentLike.comment_id == comment_id)
        .first()
    )
    if existing:
        db.delete(existing)
        comment.like_count = max(0, int(comment.like_count or 0) - 1)
        db.commit()
        db.refresh(comment)
        comment_bus.publish(comment.article_id, {"type": "liked", "comment_id": comment_id, "like_count": int(comment.like_count or 0)})
        return {"like_count": int(comment.like_count or 0), "liked": False}

    db.add(models.CommentLike(comment_id=comment_id, user_id=current.id))
    comment.like_count = int(comment.like_count or 0) + 1
    db.commit()
    db.refresh(comment)
    comment_bus.publish(comment.article_id, {"type": "liked", "comment_id": comment_id, "like_count": int(comment.like_count or 0)})
    return {"like_count": int(comment.like_count or 0), "liked": True}