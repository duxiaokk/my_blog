from __future__ import annotations

import os
import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import security
from database import get_db
from services.page_service import (
    build_about_page_data,
    build_archive_page_data,
    build_create_post_page_data,
    build_home_page_data,
    build_post_detail_page_data,
    build_top_page_data,
    create_blog_post,
    get_random_post,
    remove_blog_post,
    TECH_TAGS,
    toggle_blog_post_like,
)
from web_deps import ADMIN_USERNAME, get_optional_user, get_or_set_csrf_cookie, is_admin, verify_csrf

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
IMAGE_DIR = os.path.join(BASE_DIR, "image")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db=Depends(get_db),
    search: str = "",
    month: Optional[str] = None,
    sort: Optional[str] = None,
    user: Optional[str] = Depends(get_optional_user),
    page: int = 1,
    page_size: int = 6,
):
    context = build_home_page_data(
        db,
        username=user,
        search=search,
        month=month,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    context.update({"request": request, "user": user, "mode": "list"})
    return templates.TemplateResponse(request, "index.html", context)


@router.get("/archive", response_class=HTMLResponse)
def archive_page(
    request: Request,
    db=Depends(get_db),
    month: Optional[str] = None,
    user: Optional[str] = Depends(get_optional_user),
):
    context = build_archive_page_data(db, username=user, month=month)
    context.update({"request": request, "user": user})
    return templates.TemplateResponse(request, "index.html", context)


@router.get("/top", response_class=HTMLResponse)
def top_page(
    request: Request,
    db=Depends(get_db),
    user: Optional[str] = Depends(get_optional_user),
):
    context = build_top_page_data(db, username=user)
    context.update({"request": request, "user": user})
    return templates.TemplateResponse(request, "index.html", context)


@router.get("/random")
def random_post(db=Depends(get_db)):
    post = get_random_post(db)
    if not post:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url=f"/posts/{post.id}", status_code=status.HTTP_302_FOUND)


@router.get("/about", response_class=HTMLResponse)
def about_page(
    request: Request,
    db=Depends(get_db),
    user: Optional[str] = Depends(get_optional_user),
):
    context = build_about_page_data(db, username=user)
    context.update({"request": request, "user": user})
    return templates.TemplateResponse(request, "index.html", context)


@router.get("/posts/{post_id}", response_class=HTMLResponse)
def post_detail(
    post_id: int,
    request: Request,
    db=Depends(get_db),
    user: Optional[str] = Depends(get_optional_user),
):
    try:
        context = build_post_detail_page_data(db, post_id=post_id, username=user)
    except ValueError:
        raise HTTPException(status_code=404, detail="post not found")

    context.update({"request": request})
    response = templates.TemplateResponse(request, "detail.html", context)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@router.get("/create-post", response_class=HTMLResponse)
def create_post_page(
    request: Request,
    db=Depends(get_db),
    user: str = Depends(security.get_current_user_from_cookie),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail=f"only {ADMIN_USERNAME} can publish posts")
    preselected_tech_tag = request.query_params.get("tech_tag") or ""
    context = build_create_post_page_data(
        db,
        username=user,
        preselected_tech_tag=preselected_tech_tag,
    )
    context.update({"request": request})
    return templates.TemplateResponse(request, "create.html", context)


@router.post("/handle-create-post")
async def handle_create_post(
    title: str = Form(...),
    content: str = Form(...),
    tech_tag: str = Form(""),
    image: Optional[UploadFile] = File(None),
    db=Depends(get_db),
    user: str = Depends(security.get_current_user_from_cookie),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail=f"only {ADMIN_USERNAME} can publish posts")

    image_path = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            raise HTTPException(status_code=400, detail="only jpg/jpeg/png/gif/webp images are supported")
        filename = f"{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(IMAGE_DIR, filename)
        with open(save_path, "wb") as buffer:
            buffer.write(await image.read())
        image_path = filename

    normalized_tag = tech_tag if tech_tag in TECH_TAGS else None
    create_blog_post(db, title=title, content=content, image_path=image_path, tech_tag=normalized_tag)
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
    db=Depends(get_db),
    current_username: Optional[str] = Depends(get_optional_user),
):
    verify_csrf(request)
    result = toggle_blog_post_like(db, post_id, current_username)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    db=Depends(get_db),
    user: str = Depends(security.get_current_user_from_cookie),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail=f"only {ADMIN_USERNAME} can delete posts")

    try:
        ok = remove_blog_post(db, post_id, user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="post not found")
    return {"message": "deleted"}


@router.get("/ui/buttons", response_class=HTMLResponse)
def ui_buttons(request: Request, user: Optional[str] = Depends(get_optional_user)):
    return templates.TemplateResponse(
        request,
        "button_variants.html",
        {"request": request, "user": user, "current_user_avatar_path": None},
    )
