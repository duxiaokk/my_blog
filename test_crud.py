from __future__ import annotations

import models
from crud import crud_post as crud


def test_create_and_get_post(db_session):
    post = crud.create_post(db_session, title="Test Title", content="Test Content")
    assert post.id is not None
    got = crud.get_post(db_session, post.id)
    assert got.title == "Test Title"
    assert got.content == "Test Content"


def test_get_posts(db_session):
    crud.create_post(db_session, title="A", content="B")
    posts, total = crud.get_posts(db_session, search="A")
    assert total >= 1
    assert any(p.title == "A" for p in posts)


def test_update_post_like(db_session):
    post = crud.create_post(db_session, title="LikeTest", content="C")
    result = crud.update_post_like(db_session, post.id)
    assert result["count"] == 1

    user = models.User(username="u1", email="u1@a.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    result2 = crud.update_post_like(db_session, post.id, user.id)
    assert result2["liked"] is True
    result3 = crud.update_post_like(db_session, post.id, user.id)
    assert result3["liked"] is False


def test_delete_post(db_session):
    post = crud.create_post(db_session, title="Del", content="D")
    post_id = post.id
    ok = crud.delete_post(db_session, post_id)
    assert ok
    assert crud.get_post(db_session, post_id) is None
    raw = crud.get_post(db_session, post_id, include_deleted=True)
    assert raw is not None
    assert raw.deleted_at is not None
