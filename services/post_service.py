from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from crud.crud_post import delete_post as crud_delete_post
from crud.crud_post import get_post as crud_get_post
from crud.crud_post import get_post_like_ids
from crud.crud_post import update_post_like as crud_update_post_like
from crud.crud_user import get_user_by_username
from web_deps import is_admin


def get_post_detail_payload(db: Session, post_id: int, username: Optional[str] = None) -> dict:
    post = crud_get_post(db, post_id)
    if not post:
        raise ValueError("post not found")

    current = get_user_by_username(db, username) if username else None
    post_liked = False
    if current:
        post_liked = bool(get_post_like_ids(db, current.id, [post_id]))

    return {
        "post": post,
        "post_liked": post_liked,
        "is_admin": is_admin(username),
    }


def toggle_post_like(db: Session, post_id: int, current_username: Optional[str]) -> dict:
    current = get_user_by_username(db, current_username) if current_username else None
    user_id = current.id if current else None
    return crud_update_post_like(db, post_id, user_id)


def remove_post(db: Session, post_id: int, current_username: str) -> bool:
    if not is_admin(current_username):
        raise PermissionError("admin only")
    return crud_delete_post(db, post_id, deleted_by=current_username)
