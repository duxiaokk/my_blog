"""
模块名称：models
作用描述：定义博客系统的核心数据模型（文章、用户、评论），用于 SQLAlchemy ORM 映射数据库表结构，支持文章发布/点赞与评论的增删改查。该模块集中维护字段定义、默认值与索引策略，保证查询性能与数据一致性。
输入参数及类型：无（通过 ORM 在运行时由数据库会话调用）
返回值及类型：无（提供 ORM Model 类供业务层引用）
副作用与依赖：依赖 SQLAlchemy 与项目 database.Base；模型变更会影响数据库结构与迁移策略
作者与最后修改日期：Ado_Jk，2026-04-01
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text

from database import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    content = Column(Text)
    published = Column(Boolean, default=True)
    rating = Column(Integer, nullable=True)
    like_count = Column(Integer, default=0)
    image_path = Column(String(255), nullable=True)
    tech_tag = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by = Column(String(150), nullable=True, index=True)


class PostLike(Base):
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (Index("uq_post_likes_user_post", "user_id", "post_id", unique=True),)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    avatar_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True, index=True)

    content = Column(Text, nullable=False)
    like_count = Column(Integer, default=0, nullable=False)
    status = Column(String(32), default="active", nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_comments_article_created", "article_id", "created_at"),
        Index("ix_comments_article_parent_created", "article_id", "parent_id", "created_at"),
        Index("ix_comments_user_created", "user_id", "created_at"),
    )


class CommentLike(Base):
    __tablename__ = "comment_likes"

    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (Index("uq_comment_likes_user_comment", "user_id", "comment_id", unique=True),)


class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(80), nullable=False, index=True)
    path = Column(String(255), nullable=True, index=True)
    method = Column(String(12), nullable=True, index=True)
    status_code = Column(Integer, nullable=True, index=True)
    duration_ms = Column(Integer, nullable=True)

    username = Column(String(150), nullable=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    ab_bucket = Column(String(8), nullable=True, index=True)

    properties = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index("ix_event_logs_created", "created_at"),
        Index("ix_event_logs_event_created", "event_name", "created_at"),
        Index("ix_event_logs_session_created", "session_id", "created_at"),
    )
