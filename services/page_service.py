from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from typing import Optional, Sequence
from urllib.parse import urlencode

from sqlalchemy.orm import Session

import models
from core.config import settings
from crud.crud_post import (
    create_post,
    get_all_posts,
    get_post_like_ids,
    get_posts,
    get_random_active_post,
    get_tech_posts,
    get_tech_tag_counts,
)
from crud.crud_user import get_user_by_username
from services.post_service import get_post_detail_payload, remove_post, toggle_post_like
from web_deps import ADMIN_USERNAME, is_admin

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_DIR = os.path.join(BASE_DIR, "image")
TECH_TAGS = settings.tech_tags


def get_month_key(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m")


def resolve_avatar_path(stored_path: str) -> Optional[str]:
    normalized = stored_path.replace("\\", "/").lstrip("/")
    candidates = [normalized]
    if normalized.startswith("avatars/"):
        candidates.append(normalized[len("avatars/") :])
    else:
        candidates.append(f"avatars/{normalized}")

    for candidate in candidates:
        if os.path.exists(os.path.join(IMAGE_DIR, candidate)):
            return candidate
    return normalized if os.path.exists(os.path.join(IMAGE_DIR, normalized)) else None


def get_current_user_profile(db: Session, username: Optional[str]) -> dict[str, Optional[str]]:
    if not username:
        return {"avatar_path": None}
    user = get_user_by_username(db, username)
    if not user or not user.avatar_path:
        return {"avatar_path": None}
    return {"avatar_path": resolve_avatar_path(user.avatar_path)}


def build_home_page_data(
    db: Session,
    *,
    username: Optional[str],
    search: str = "",
    month: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = 1,
    page_size: int = 6,
    tech_tags: Sequence[str] = TECH_TAGS,
) -> dict:
    skip = (page - 1) * page_size
    posts, total_count = get_posts(
        db,
        search=search,
        month=month,
        sort=sort,
        tech_scope="general",
        tech_tags=tech_tags,
        skip=skip,
        limit=page_size,
    )

    page_title = ""
    if month:
        page_title = f"Archive: {month}"
    elif sort == "top":
        page_title = "Top Posts"

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
    params = {}
    if search:
        params["search"] = search
    if month:
        params["month"] = month
    if sort:
        params["sort"] = sort
    page_query = urlencode(params)
    pagination_base = f"/?{page_query}&page=" if page_query else "/?page="

    liked_post_ids: set[int] = set()
    if username and posts:
        user = get_user_by_username(db, username)
        if user:
            liked_post_ids = get_post_like_ids(db, user.id, [int(post.id) for post in posts])

    return {
        "posts": posts,
        "search": search,
        "month": month,
        "page_title": page_title,
        "liked_post_ids": list(liked_post_ids),
        "featured_posts": posts,
        "is_admin": is_admin(username),
        "current_user_avatar_path": get_current_user_profile(db, username)["avatar_path"],
        "pagination_base": pagination_base,
        "page": page,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


def build_archive_page_data(
    db: Session,
    *,
    username: Optional[str],
    month: Optional[str] = None,
) -> dict:
    posts = get_all_posts(db)
    profile = get_current_user_profile(db, username)
    if month:
        filtered = [
            post for post in posts if get_month_key(getattr(post, "created_at", None)) == month
        ]
        return {
            "mode": "list",
            "posts": filtered,
            "search": "",
            "month": month,
            "page_title": f"Archive: {month}",
            "featured_posts": filtered,
            "is_admin": is_admin(username),
            "current_user_avatar_path": profile["avatar_path"],
        }

    counts: dict[str, int] = {}
    for post in posts:
        key = get_month_key(getattr(post, "created_at", None))
        if key:
            counts[key] = counts.get(key, 0) + 1

    archives = [
        {"month": key, "count": count}
        for key, count in sorted(counts.items(), key=lambda item: item[0], reverse=True)
    ]
    return {
        "mode": "archive",
        "posts": [],
        "search": "",
        "archives": archives,
        "is_admin": is_admin(username),
        "current_user_avatar_path": profile["avatar_path"],
    }


def build_top_page_data(db: Session, *, username: Optional[str]) -> dict:
    profile = get_current_user_profile(db, username)
    tech_counts = get_tech_tag_counts(db, TECH_TAGS)
    tech_posts = get_tech_posts(db, TECH_TAGS)
    tech_posts_by_tag: dict[str, list[models.Post]] = {tag: [] for tag in TECH_TAGS}
    for post in tech_posts:
        if post.tech_tag in tech_posts_by_tag:
            tech_posts_by_tag[post.tech_tag].append(post)

    tech_stack = [
        {
            "name": tag,
            "mark": tag[:1],
            "article_count": tech_counts.get(tag, 0),
            "publish_label": f"Publish #{tag}",
            "action_url": f"/create-post?{urlencode({'tech_tag': tag})}"
            if is_admin(username)
            else "/login",
        }
        for tag in TECH_TAGS
    ]
    return {
        "mode": "tech",
        "posts": [],
        "search": "",
        "page_title": "Tech Stack",
        "tech_tags": TECH_TAGS,
        "tech_stack": tech_stack,
        "tech_posts": tech_posts,
        "tech_posts_by_tag": tech_posts_by_tag,
        "is_admin": is_admin(username),
        "current_user_avatar_path": profile["avatar_path"],
    }


def build_about_page_data(db: Session, *, username: Optional[str]) -> dict:
    profile = get_current_user_profile(db, username)
    return {
        "mode": "about",
        "posts": [],
        "search": "",
        "is_admin": is_admin(username),
        "current_user_avatar_path": profile["avatar_path"],
    }


def build_post_detail_page_data(
    db: Session,
    *,
    post_id: int,
    username: Optional[str],
) -> dict:
    payload = get_post_detail_payload(db, post_id, username)
    profile = get_current_user_profile(db, username)
    return {
        "post": payload["post"],
        "user": username,
        "author_name": ADMIN_USERNAME,
        "post_liked": payload["post_liked"],
        "is_admin": is_admin(username),
        "current_user_avatar_path": profile["avatar_path"],
    }


def build_create_post_page_data(
    db: Session,
    *,
    username: str,
    preselected_tech_tag: str,
) -> dict:
    profile = get_current_user_profile(db, username)
    return {
        "user": username,
        "current_user_avatar_path": profile["avatar_path"],
        "tech_tags": TECH_TAGS,
        "preselected_tech_tag": preselected_tech_tag if preselected_tech_tag in TECH_TAGS else "",
    }


def create_blog_post(
    db: Session,
    *,
    title: str,
    content: str,
    image_path: str | None = None,
    tech_tag: str | None = None,
) -> models.Post:
    return create_post(db, title=title, content=content, image_path=image_path, tech_tag=tech_tag)


def get_random_post(db: Session) -> Optional[models.Post]:
    return get_random_active_post(db)


def remove_blog_post(db: Session, post_id: int, username: str) -> bool:
    return remove_post(db, post_id, username)


def toggle_blog_post_like(db: Session, post_id: int, username: Optional[str]) -> dict:
    return toggle_post_like(db, post_id, username)
