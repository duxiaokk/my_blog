from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

import models


def create_post(
    db: Session,
    title: str,
    content: str,
    image_path: str | None = None,
    tech_tag: str | None = None,
) -> models.Post:
    new_post = models.Post(title=title, content=content, image_path=image_path, tech_tag=tech_tag)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


def get_post(db: Session, post_id: int, include_deleted: bool = False) -> Optional[models.Post]:
    query = db.query(models.Post).filter(models.Post.id == post_id)
    if not include_deleted:
        query = query.filter(models.Post.deleted_at.is_(None))
    return query.first()


def get_posts(
    db: Session,
    search: str = "",
    month: Optional[str] = None,
    sort: Optional[str] = None,
    tech_scope: str = "all",
    tech_tags: Sequence[str] = (),
    skip: int = 0,
    limit: int = 10,
    include_deleted: bool = False,
) -> Tuple[List[models.Post], int]:
    query = db.query(models.Post)

    if not include_deleted:
        query = query.filter(models.Post.deleted_at.is_(None))

    if search:
        query = query.filter(models.Post.title.contains(search))

    if tech_scope == "general" and tech_tags:
        query = query.filter(
            or_(models.Post.tech_tag.is_(None), ~models.Post.tech_tag.in_(list(tech_tags)))
        )
    elif tech_scope == "tech" and tech_tags:
        query = query.filter(models.Post.tech_tag.in_(list(tech_tags)))

    if month:
        try:
            start_date = datetime.strptime(month, "%Y-%m").replace(day=1)
        except ValueError:
            return [], 0
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1)
        query = query.filter(
            models.Post.created_at >= start_date, models.Post.created_at < end_date
        )

    if sort == "top":
        query = query.order_by(models.Post.like_count.desc(), models.Post.id.desc())
    else:
        query = query.order_by(models.Post.id.desc())

    total_count = query.count()
    posts = query.offset(skip).limit(limit).all()
    return posts, total_count


def get_all_posts(db: Session, include_deleted: bool = False) -> list[models.Post]:
    query = db.query(models.Post)
    if not include_deleted:
        query = query.filter(models.Post.deleted_at.is_(None))
    return query.order_by(models.Post.id.desc()).all()


def get_random_active_post(db: Session) -> Optional[models.Post]:
    return (
        db.query(models.Post)
        .filter(models.Post.deleted_at.is_(None))
        .order_by(func.random())
        .first()
    )


def get_tech_posts(db: Session, tech_tags: Sequence[str]) -> list[models.Post]:
    if not tech_tags:
        return []
    return (
        db.query(models.Post)
        .filter(models.Post.deleted_at.is_(None), models.Post.tech_tag.in_(list(tech_tags)))
        .order_by(models.Post.id.desc())
        .all()
    )


def get_tech_tag_counts(db: Session, tech_tags: Sequence[str]) -> dict[str, int]:
    if not tech_tags:
        return {}
    rows = (
        db.query(models.Post.tech_tag, func.count(models.Post.id))
        .filter(models.Post.deleted_at.is_(None), models.Post.tech_tag.in_(list(tech_tags)))
        .group_by(models.Post.tech_tag)
        .all()
    )
    counts = {tag: 0 for tag in tech_tags}
    for tag, count in rows:
        if tag is not None:
            counts[str(tag)] = int(count)
    return counts


def update_post_like(db: Session, post_id: int, user_id: Optional[int] = None) -> dict:
    post = (
        db.query(models.Post)
        .filter(models.Post.id == post_id, models.Post.deleted_at.is_(None))
        .first()
    )
    if not post:
        return {"error": "文章不存在"}

    if user_id is None:
        post.like_count = int(post.like_count or 0) + 1
        db.commit()
        return {"count": post.like_count, "liked": False}

    existing = (
        db.query(models.PostLike)
        .filter(models.PostLike.user_id == user_id, models.PostLike.post_id == post_id)
        .first()
    )
    if existing:
        db.delete(existing)
        post.like_count = max(0, int(post.like_count or 0) - 1)
        liked = False
    else:
        db.add(models.PostLike(post_id=post_id, user_id=user_id))
        post.like_count = int(post.like_count or 0) + 1
        liked = True

    db.commit()
    db.refresh(post)
    return {"count": post.like_count, "liked": liked}


def get_post_like_ids(db: Session, user_id: int, post_ids: Sequence[int]) -> set[int]:
    if not post_ids:
        return set()
    liked_rows = (
        db.query(models.PostLike.post_id)
        .filter(models.PostLike.user_id == user_id, models.PostLike.post_id.in_(list(post_ids)))
        .all()
    )
    return {int(row[0]) for row in liked_rows}


def delete_post(db: Session, post_id: int, deleted_by: str | None = None) -> bool:
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        return False

    if post.deleted_at is None:
        post.deleted_at = datetime.now(timezone.utc)
        post.deleted_by = deleted_by
    db.commit()
    return True
