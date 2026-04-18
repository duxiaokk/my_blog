from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

import models


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()

