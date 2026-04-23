from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PostBase(BaseModel):
    title: str = Field(..., min_length=1)
    content: str
    published: bool = True
    rating: Optional[int] = Field(None, ge=0, le=5)


class PostCreate(PostBase):
    pass


class ArticleCreate(PostBase):
    pass
