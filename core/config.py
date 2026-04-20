from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    _HAS_PYDANTIC_SETTINGS = True
except Exception:  # pragma: no cover - fallback for older/local envs
    from pydantic import BaseModel

    BaseSettings = BaseModel  # type: ignore[assignment]
    SettingsConfigDict = None  # type: ignore[assignment]
    _HAS_PYDANTIC_SETTINGS = False


BASE_DIR = Path(__file__).resolve().parent.parent


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None and value != "" else default
    except ValueError:
        return default


def _parse_tags(raw: str | None) -> List[str]:
    if not raw:
        return ["Python", "FastAPI", "SQLAlchemy", "SQLite"]
    tags = [item.strip() for item in raw.split(",") if item.strip()]
    return tags or ["Python", "FastAPI", "SQLAlchemy", "SQLite"]


class Settings(BaseSettings):
    if _HAS_PYDANTIC_SETTINGS:
        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: Optional[str] = None
    use_mysql: bool = False
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_host: str = "127.0.0.1"
    db_port: str = "3306"
    db_name: Optional[str] = None
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    admin_username: str = "Ado_Jk"
    tech_tags_raw: str = "Python,FastAPI,SQLAlchemy,SQLite"
    zhipuai_api_key: Optional[str] = None
    redis_url: Optional[str] = None

    @property
    def tech_tags(self) -> list[str]:
        return _parse_tags(self.tech_tags_raw)

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if self.use_mysql:
            if not self.db_user or not self.db_password or not self.db_name:
                raise ValueError("MySQL configuration requires DB_USER, DB_PASSWORD and DB_NAME")
            return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        sqlite_db_path = BASE_DIR / "blog.db"
        return f"sqlite:///{str(sqlite_db_path).replace(os.sep, '/')}"


def _load_fallback_settings() -> Settings:
    return Settings.model_validate(
        {
            "database_url": os.getenv("DATABASE_URL") or None,
            "use_mysql": _parse_bool(os.getenv("USE_MYSQL"), False),
            "db_user": os.getenv("DB_USER") or None,
            "db_password": os.getenv("DB_PASSWORD") or None,
            "db_host": os.getenv("DB_HOST", "127.0.0.1"),
            "db_port": os.getenv("DB_PORT", "3306"),
            "db_name": os.getenv("DB_NAME") or None,
            "secret_key": os.getenv("SECRET_KEY", ""),
            "jwt_algorithm": os.getenv("ALGORITHM", "HS256"),
            "access_token_expire_minutes": _parse_int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"), 30),
            "refresh_token_expire_days": _parse_int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"), 30),
            "admin_username": os.getenv("ADMIN_USERNAME", "Ado_Jk"),
            "tech_tags_raw": os.getenv("TECH_TAGS", "Python,FastAPI,SQLAlchemy,SQLite"),
            "zhipuai_api_key": os.getenv("ZHIPUAI_API_KEY"),
            "redis_url": os.getenv("REDIS_URL") or None,
        }
    )


settings = Settings() if _HAS_PYDANTIC_SETTINGS else _load_fallback_settings()

if not settings.secret_key:
    raise RuntimeError("SECRET_KEY is required")
