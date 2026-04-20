from __future__ import annotations

import math
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Set
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import security
from core.config import settings
from crud.crud_post import create_post, get_posts
from database import get_db
from services import post_service
from web_deps import ADMIN_USERNAME, get_optional_user, get_or_set_csrf_cookie, is_admin, verify_csrf

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
IMAGE_DIR = os.path.join(BASE_DIR, "image")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
TECH_TAGS = settings.tech_tags

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATES_DIR)


def _get_tech_tag_counts(db: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for tag in TECH_TAGS:
        counts[tag] = (
            db.query(models.Post.id)
            .filter(models.Post.deleted_at.is_(None), models.Post.tech_tag == tag)
            .count()
        )
    return counts


def _group_tech_posts_by_tag(posts: list[models.Post]) -> dict[str, list[models.Post]]:
    grouped: dict[str, list[models.Post]] = {tag: [] for tag in TECH_TAGS}
    for post in posts:
        if post.tech_tag in grouped:
            grouped[post.tech_tag].append(post)
    return grouped


def get_month_key(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m")


def _get_liked_post_ids(db: Session, username: Optional[str], posts: list[models.Post]) -> Set[int]:
    if not username or not posts:
        return set()
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return set()

    post_ids = [int(p.id) for p in posts]
    liked_rows = (
        db.query(models.PostLike.post_id)
        .filter(models.PostLike.user_id == user.id, models.PostLike.post_id.in_(post_ids))
        .all()
    )
    return {int(row[0]) for row in liked_rows}


def _get_current_user_profile(db: Session, username: Optional[str]) -> dict[str, Optional[str]]:
    if not username:
        return {"avatar_path": None}
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not user.avatar_path:
        return {"avatar_path": None}
    return {"avatar_path": _resolve_avatar_path(user.avatar_path)}


def _resolve_avatar_path(stored_path: str) -> Optional[str]:
    candidates = []
    normalized = stored_path.replace("\\", "/").lstrip("/")
    candidates.append(normalized)

    if normalized.startswith("avatars/"):
        candidates.append(normalized[len("avatars/") :])
    else:
        candidates.append(f"avatars/{normalized}")

    for candidate in candidates:
        abs_path = os.path.join(IMAGE_DIR, candidate)
        if os.path.exists(abs_path):
            return candidate

    return normalized if os.path.exists(os.path.join(IMAGE_DIR, normalized)) else None


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: Session = Depends(get_db),
    search: str = "",
    month: Optional[str] = None,
    sort: Optional[str] = None,
    user: Optional[str] = Depends(get_optional_user),
    page: int = 1,
    page_size: int = 6,
):
    skip = (page - 1) * page_size
    posts, total_count = get_posts(
        db,
        search=search,
        month=month,
        sort=sort,
        tech_scope="general",
        tech_tags=TECH_TAGS,
        skip=skip,
        limit=page_size,
    )

    page_title = ""
    if month:
        page_title = f"归档：{month}"
    elif sort == "top":
        page_title = "技术栈"

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
    has_prev = page > 1
    has_next = page < total_pages

    liked_post_ids = _get_liked_post_ids(db, user, posts)
    current_user_profile = _get_current_user_profile(db, user)
    page_params = {}
    if search:
        page_params["search"] = search
    if month:
        page_params["month"] = month
    if sort:
        page_params["sort"] = sort
    page_query = urlencode(page_params)
    pagination_base = f"/?{page_query}&page=" if page_query else "/?page="

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "posts": posts,
            "search": search,
            "user": user,
            "mode": "list",
            "month": month,
            "page_title": page_title,
            "liked_post_ids": list(liked_post_ids),
            "featured_posts": posts,
            "is_admin": is_admin(user),
            "current_user_avatar_path": current_user_profile["avatar_path"],
            "pagination_base": pagination_base,
            "page": page,
            "total_pages": total_pages,
            "has_prev": has_prev,
            "has_next": has_next,
        },
    )


@router.get("/archive", response_class=HTMLResponse)
def archive_page(
    request: Request,
    db: Session = Depends(get_db),
    month: Optional[str] = None,
    user: Optional[str] = Depends(get_optional_user),
):
    posts = db.query(models.Post).filter(models.Post.deleted_at.is_(None)).order_by(models.Post.id.desc()).all()
    current_user_profile = _get_current_user_profile(db, user)
    if month:
        filtered = [post for post in posts if get_month_key(getattr(post, "created_at", None)) == month]
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "request": request,
                "posts": filtered,
                "search": "",
                "user": user,
                "mode": "list",
                "month": month,
                "page_title": f"归档：{month}",
                "featured_posts": filtered,
                "is_admin": is_admin(user),
                "current_user_avatar_path": current_user_profile["avatar_path"],
            },
        )

    counts: dict[str, int] = {}
    for post in posts:
        key = get_month_key(getattr(post, "created_at", None))
        if key and len(key) == 7 and key[4] == "-":
            counts[key] = counts.get(key, 0) + 1

    archives = [{"month": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: x[0], reverse=True)]
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "posts": [],
            "search": "",
            "user": user,
            "mode": "archive",
            "archives": archives,
            "is_admin": is_admin(user),
            "current_user_avatar_path": current_user_profile["avatar_path"],
        },
    )


@router.get("/top", response_class=HTMLResponse)
def top_page(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[str] = Depends(get_optional_user),
):
    current_user_profile = _get_current_user_profile(db, user)
    tech_counts = _get_tech_tag_counts(db)
    tech_query = db.query(models.Post).filter(models.Post.deleted_at.is_(None), models.Post.tech_tag.in_(TECH_TAGS))
    tech_posts = tech_query.order_by(models.Post.id.desc()).all()
    tech_posts_by_tag = _group_tech_posts_by_tag(tech_posts)
    tech_stack = [
        {
            "name": tag,
            "mark": tag[:1],
            "article_count": tech_counts[tag],
            "publish_label": f"Publish #{tag}",
            "action_url": f"/create-post?{urlencode({'tech_tag': tag})}" if is_admin(user) else "/login",
        }
        for tag in TECH_TAGS
    ]
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "posts": [],
            "search": "",
            "user": user,
            "mode": "tech",
            "page_title": "技术栈",
            "tech_tags": TECH_TAGS,
            "tech_stack": tech_stack,
            "tech_posts": tech_posts,
            "tech_posts_by_tag": tech_posts_by_tag,
            "is_admin": is_admin(user),
            "current_user_avatar_path": current_user_profile["avatar_path"],
        },
    )


@router.get("/random")
def random_post(db: Session = Depends(get_db)):
    post = db.query(models.Post).filter(models.Post.deleted_at.is_(None)).order_by(func.random()).first()
    if not post:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url=f"/posts/{post.id}", status_code=status.HTTP_302_FOUND)


@router.get("/about", response_class=HTMLResponse)
def about_page(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[str] = Depends(get_optional_user),
):
    current_user_profile = _get_current_user_profile(db, user)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "posts": [],
            "search": "",
            "user": user,
            "mode": "about",
            "is_admin": is_admin(user),
            "current_user_avatar_path": current_user_profile["avatar_path"],
        },
    )


@router.get("/posts/{post_id}", response_class=HTMLResponse)
def post_detail(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[str] = Depends(get_optional_user),
):
    try:
        payload = post_service.get_post_detail_payload(db, post_id, user)
    except ValueError:
        raise HTTPException(status_code=404, detail="文章不存在")

    post = payload["post"]
    current_user_profile = _get_current_user_profile(db, user)

    response = templates.TemplateResponse(
        request,
        "detail.html",
        {
            "request": request,
            "post": post,
            "user": user,
            "author_name": ADMIN_USERNAME,
            "post_liked": payload["post_liked"],
            "is_admin": is_admin(user),
            "current_user_avatar_path": current_user_profile["avatar_path"],
        },
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@router.get("/create-post", response_class=HTMLResponse)
def create_post_page(request: Request, db: Session = Depends(get_db), user: str = Depends(security.get_current_user_from_cookie)):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail=f"只有管理员 {ADMIN_USERNAME} 可以发布文章")
    preselected_tech_tag = request.query_params.get("tech_tag") or ""
    if preselected_tech_tag not in TECH_TAGS:
        preselected_tech_tag = ""
    return templates.TemplateResponse(
        request,
        "create.html",
        {
            "request": request,
            "user": user,
            "current_user_avatar_path": _get_current_user_profile(db, user)["avatar_path"],
            "tech_tags": TECH_TAGS,
            "preselected_tech_tag": preselected_tech_tag,
        },
    )


@router.post("/handle-create-post")
async def handle_create_post(
    title: str = Form(...),
    content: str = Form(...),
    tech_tag: str = Form(""),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: str = Depends(security.get_current_user_from_cookie),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail=f"只有管理员 {ADMIN_USERNAME} 可以发布文章")

    image_path = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            raise HTTPException(status_code=400, detail="仅支持 jpg/jpeg/png/gif/webp 图片")
        filename = f"{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(IMAGE_DIR, filename)
        with open(save_path, "wb") as buffer:
            buffer.write(await image.read())
        image_path = filename

    normalized_tag = tech_tag if tech_tag in TECH_TAGS else None
    create_post(db, title=title, content=content, image_path=image_path, tech_tag=normalized_tag)
    redirect_url = "/top" if normalized_tag else "/"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/csrf-token")
def csrf_token(request: Request, response: Response):
    token = get_or_set_csrf_cookie(request, response)
    return {"csrf_token": token}


@router.post("/posts/{post_id}/like")
def like_post(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_username: Optional[str] = Depends(get_optional_user),
):
    verify_csrf(request)
    result = post_service.toggle_post_like(db, post_id, current_username)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(security.get_current_user_from_cookie),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail=f"只有管理员 {ADMIN_USERNAME} 可以删除文章")

    try:
        ok = post_service.remove_post(db, post_id, user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="找不到该文章")
    return {"message": "已删除"}


@router.get("/ui/buttons", response_class=HTMLResponse)
def ui_buttons(request: Request, user: Optional[str] = Depends(get_optional_user)):
    return templates.TemplateResponse(request, "button_variants.html", {"request": request, "user": user, "current_user_avatar_path": None})
