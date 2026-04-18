from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

import models


def create_post(db: Session, title: str, content: str, image_path: str | None = None, tech_tag: str | None = None) -> models.Post:
    new_post = models.Post(title=title, content=content, image_path=image_path, tech_tag=tech_tag)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


def get_post(db: Session, post_id: int) -> Optional[models.Post]:
    return db.query(models.Post).filter(models.Post.id == post_id).first()


def get_posts(
    db: Session,
    search: str = "",
    month: Optional[str] = None,
    sort: Optional[str] = None,
    tech_scope: str = "all",
    tech_tags: Sequence[str] = (),
    skip: int = 0,
    limit: int = 10,
) -> Tuple[List[models.Post], int]:
    query = db.query(models.Post)

    if search:
        query = query.filter(models.Post.title.contains(search))

    if tech_scope == "general" and tech_tags:
        query = query.filter(or_(models.Post.tech_tag.is_(None), ~models.Post.tech_tag.in_(list(tech_tags))))
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
        query = query.filter(models.Post.created_at >= start_date, models.Post.created_at < end_date)

    if sort == "top":
        query = query.order_by(models.Post.like_count.desc(), models.Post.id.desc())
    else:
        query = query.order_by(models.Post.id.desc())

    total_count = query.count()
    posts = query.offset(skip).limit(limit).all()
    return posts, total_count


def update_post_like(db: Session, post_id: int, user_id: Optional[int] = None) -> dict:
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
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


def delete_post(db: Session, post_id: int) -> bool:
    post_query = db.query(models.Post).filter(models.Post.id == post_id)
    post = post_query.first()
    if not post:
        return False

    comment_ids = [row[0] for row in db.query(models.Comment.id).filter(models.Comment.article_id == post_id).all()]
    if comment_ids:
        db.query(models.CommentLike).filter(models.CommentLike.comment_id.in_(comment_ids)).delete(synchronize_session=False)
        db.query(models.Comment).filter(models.Comment.id.in_(comment_ids)).delete(synchronize_session=False)

    post_query.delete(synchronize_session=False)
    db.commit()
    return True

