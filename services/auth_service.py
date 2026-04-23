from __future__ import annotations

from sqlalchemy.orm import Session

import security
from crud.crud_user import (
    create_user,
    get_user_by_username,
    get_user_by_username_or_email,
    update_user_avatar,
)


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not security.verify_password(password, user.hashed_password):
        return None
    return user


def register_user(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    avatar_path: str | None = None,
):
    username = (username or "").strip()
    email = (email or "").strip()
    password = (password or "").strip()

    if not username or not password:
        raise ValueError("Missing registration data")
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")

    email = email or f"{username}@local.invalid"
    existing = get_user_by_username_or_email(db, username, email)
    if existing:
        raise ValueError("Username or email already exists")

    hashed_pwd = security.get_password_hash(password)
    return create_user(
        db,
        username=username,
        email=email,
        hashed_password=hashed_pwd,
        avatar_path=avatar_path,
    )


def change_user_avatar(db: Session, *, username: str, avatar_path: str):
    user = get_user_by_username(db, username)
    if not user:
        raise LookupError("User not found")
    return update_user_avatar(db, user, avatar_path)
