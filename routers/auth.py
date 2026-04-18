from __future__ import annotations

import logging
import os
import sys
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
import models
from schemas.user import Token, UserLogin
import security


router = APIRouter(tags=["Authentication"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
AVATAR_DIR = os.path.join(BASE_DIR, "image", "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth_audit")


@router.post("/login", response_model=Token)
async def login_api(data: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == data.username).first()

    if not user or not security.verify_password(data.password, user.hashed_password):
        logger.warning(f"login failed: username={data.username}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Username or password is incorrect")

    logger.info(f"login success: {user.username}")
    access_token = security.create_access_token(data={"sub": user.username})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.get("/register-page", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


async def _parse_register_request(request: Request) -> tuple[str | None, str | None, str | None, UploadFile | None]:
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        data = await request.json()
        return data.get("username"), data.get("email"), data.get("password"), None

    form = await request.form()
    avatar = form.get("avatar")
    if not isinstance(avatar, UploadFile):
        avatar = None
    return form.get("username"), form.get("email"), form.get("password"), avatar


async def _save_avatar_file(avatar: UploadFile | None) -> str | None:
    if not avatar or not avatar.filename:
        return None

    ext = os.path.splitext(avatar.filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        raise HTTPException(status_code=400, detail="Only jpg/jpeg/png/gif/webp avatars are supported")

    saved_name = f"{uuid.uuid4().hex}{ext}"
    rel_path = f"avatars/{saved_name}"
    abs_path = os.path.join(AVATAR_DIR, saved_name)

    file_data = await avatar.read()
    with open(abs_path, "wb") as buffer:
        buffer.write(file_data)

    return rel_path.replace("\\", "/")


async def _save_uploaded_avatar(avatar: UploadFile) -> str:
    if not avatar.filename:
        raise HTTPException(status_code=400, detail="请选择头像文件")

    ext = os.path.splitext(avatar.filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        raise HTTPException(status_code=400, detail="Only jpg/jpeg/png/gif/webp avatars are supported")

    saved_name = f"{uuid.uuid4().hex}{ext}"
    rel_path = f"avatars/{saved_name}"
    abs_path = os.path.join(AVATAR_DIR, saved_name)
    file_data = await avatar.read()
    with open(abs_path, "wb") as buffer:
        buffer.write(file_data)
    return rel_path.replace("\\", "/")


@router.post("/register")
async def register_user(request: Request, db: Session = Depends(get_db)):
    username, email, password, avatar = await _parse_register_request(request)

    username = (username or "").strip()
    password = (password or "").strip()
    email = (email or "").strip() or f"{username}@local.invalid"

    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing registration data")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing = db.query(models.User).filter(
        (models.User.username == username) | (models.User.email == email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    avatar_path = await _save_avatar_file(avatar)
    hashed_pwd = security.get_password_hash(password)
    new_user = models.User(
        username=username,
        email=email,
        hashed_password=hashed_pwd,
        avatar_path=avatar_path,
    )
    db.add(new_user)
    db.commit()

    access_token = security.create_access_token(data={"sub": username})
    wants_json = "application/json" in (request.headers.get("content-type") or "").lower() or (
        request.headers.get("x-requested-with") or ""
    ).lower() == "xmlhttprequest"

    if wants_json:
        response = JSONResponse(
            {"message": "Registration successful", "access_token": access_token, "token_type": "bearer", "avatar_path": avatar_path}
        )
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return response

    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response


@router.post("/profile/avatar")
async def update_profile_avatar(
    request: Request,
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    username = security.get_current_user_from_cookie(request)
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    avatar_path = await _save_uploaded_avatar(avatar)
    user.avatar_path = avatar_path
    db.add(user)
    db.commit()
    return {"message": "头像已更新", "avatar_path": avatar_path}
