from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from crud.crud_post import delete_post as crud_delete_post
from crud.crud_post import get_post as crud_get_post
from crud.crud_post import update_post_like as crud_update_post_like
import models
from web_deps import is_admin


def get_post_detail_payload(db: Session, post_id: int, username: Optional[str] = None) -> dict:
    post = crud_get_post(db, post_id)
    if not post:
        raise ValueError("post not found")

    current = db.query(models.User).filter(models.User.username == username).first() if username else None
    post_liked = False
    if current:
        liked = (
            db.query(models.PostLike.id)
            .filter(models.PostLike.user_id == current.id, models.PostLike.post_id == post_id)
            .first()
        )
        post_liked = bool(liked)

    return {
        "post": post,
        "post_liked": post_liked,
        "is_admin": is_admin(username),
    }


def toggle_post_like(db: Session, post_id: int, current_username: Optional[str]) -> dict:
    current = db.query(models.User).filter(models.User.username == current_username).first() if current_username else None
    user_id = current.id if current else None
    return crud_update_post_like(db, post_id, user_id)


def remove_post(db: Session, post_id: int, current_username: str) -> bool:
    if not is_admin(current_username):
        raise PermissionError("admin only")
    return crud_delete_post(db, post_id, deleted_by=current_username)
