from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from services.post_service import get_post_detail_payload, remove_post, toggle_post_like
from web_deps import get_optional_user, verify_csrf

router = APIRouter(prefix="/api/v1/posts", tags=["Posts API"])


@router.get("/{post_id}")
def get_post_detail(
    post_id: int,
    db: Session = Depends(get_db),
    current_username: str | None = Depends(get_optional_user),
):
    try:
        payload = get_post_detail_payload(db, post_id, current_username)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    post = payload["post"]
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "like_count": int(post.like_count or 0),
        "image_path": post.image_path,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "author_name": "Ado_Jk",
        "liked": payload["post_liked"],
    }


@router.post("/{post_id}/like")
def like_post(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_username: str | None = Depends(get_optional_user),
):
    verify_csrf(request)
    result = toggle_post_like(db, post_id, current_username)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_username: str | None = Depends(get_optional_user),
):
    verify_csrf(request)
    if not current_username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not logged in")
    try:
        ok = remove_post(db, post_id, current_username)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="post not found")
    return {"message": "deleted"}
