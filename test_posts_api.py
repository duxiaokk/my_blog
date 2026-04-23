from __future__ import annotations

import models
import security
from crud import crud_post as crud


def test_like_post_toggles_for_authenticated_user(client, db_session):
    post = crud.create_post(db_session, title="Like target", content="Content")
    db_session.add(
        models.User(
            username="tester",
            email="tester@example.com",
            hashed_password=security.get_password_hash("correct-password"),
        )
    )
    db_session.commit()

    csrf_token = "csrf-token"
    access_token = security.create_access_token({"sub": "tester"})
    client.cookies.set("csrf_token", csrf_token)
    client.cookies.set("access_token", access_token)

    response = client.post(
        f"/api/v1/posts/{post.id}/like",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 200
    assert response.json() == {"count": 1, "liked": True}

    response = client.post(
        f"/api/v1/posts/{post.id}/like",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 200
    assert response.json() == {"count": 0, "liked": False}


def test_delete_post_rejects_non_admin_user(client, db_session):
    post = crud.create_post(db_session, title="Delete target", content="Content")
    db_session.add(
        models.User(
            username="tester",
            email="tester@example.com",
            hashed_password=security.get_password_hash("correct-password"),
        )
    )
    db_session.commit()

    client.cookies.set("access_token", security.create_access_token({"sub": "tester"}))
    response = client.delete(f"/api/v1/posts/{post.id}")

    assert response.status_code == 403
    assert "detail" in response.json()

    still_there = crud.get_post(db_session, post.id, include_deleted=True)
    assert still_there is not None
    assert still_there.deleted_at is None
