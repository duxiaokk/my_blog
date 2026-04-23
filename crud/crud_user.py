from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

import models


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_username_or_email(db: Session, username: str, email: str) -> Optional[models.User]:
    return (
        db.query(models.User)
        .filter((models.User.username == username) | (models.User.email == email))
        .first()
    )


def create_user(
    db: Session,
    *,
    username: str,
    email: str,
    hashed_password: str,
    avatar_path: str | None = None,
) -> models.User:
    user = models.User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        avatar_path=avatar_path,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_avatar(db: Session, user: models.User, avatar_path: str | None) -> models.User:
    user.avatar_path = avatar_path
    db.commit()
    db.refresh(user)
    return user
