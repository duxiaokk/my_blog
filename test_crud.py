"""
test_crud.py
单元测试：my_blog.crud
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from crud import crud_post as crud
from database import Base
import models


@pytest.fixture(scope="module")
def db():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()


def test_create_and_get_post(db):
    post = crud.create_post(db, title="Test Title", content="Test Content")
    assert post.id is not None
    got = crud.get_post(db, post.id)
    assert got.title == "Test Title"
    assert got.content == "Test Content"


def test_get_posts(db):
    crud.create_post(db, title="A", content="B")
    posts, total = crud.get_posts(db, search="A")
    assert total >= 1
    assert any(p.title == "A" for p in posts)


def test_update_post_like(db):
    post = crud.create_post(db, title="LikeTest", content="C")
    result = crud.update_post_like(db, post.id)
    assert result["count"] == 1

    user = models.User(username="u1", email="u1@a.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    result2 = crud.update_post_like(db, post.id, user.id)
    assert result2["liked"] is True
    result3 = crud.update_post_like(db, post.id, user.id)
    assert result3["liked"] is False


def test_delete_post(db):
    post = crud.create_post(db, title="Del", content="D")
    post_id = post.id
    ok = crud.delete_post(db, post_id)
    assert ok
    assert crud.get_post(db, post_id) is None
    raw = crud.get_post(db, post_id, include_deleted=True)
    assert raw is not None
    assert raw.deleted_at is not None
