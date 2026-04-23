from __future__ import annotations

from fastapi.testclient import TestClient

import models
import security


def test_register_json_creates_user_and_sets_cookie(client: TestClient, db_session):
    response = client.post(
        "/register",
        json={
            "username": "new-user",
            "email": "new-user@example.com",
            "password": "strong-password",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Registration successful",
        "token_type": "bearer",
        "avatar_path": None,
    }
    assert "access_token" in response.cookies

    created = db_session.query(models.User).filter(models.User.username == "new-user").first()
    assert created is not None
    assert created.email == "new-user@example.com"


def test_login_success_sets_access_cookie(client: TestClient, db_session):
    db_session.add(
        models.User(
            username="tester",
            email="tester@example.com",
            hashed_password=security.get_password_hash("correct-password"),
        )
    )
    db_session.commit()

    response = client.post(
        "/login",
        json={"username": "tester", "password": "correct-password", "remember": False},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Login successful",
        "token_type": "bearer",
        "avatar_path": None,
    }
    assert "access_token" in response.cookies


def test_login_with_wrong_password_keeps_specific_error_message(client: TestClient, db_session):
    db_session.add(
        models.User(
            username="tester",
            email="tester@example.com",
            hashed_password=security.get_password_hash("correct-password"),
        )
    )
    db_session.commit()

    response = client.post(
        "/login",
        json={"username": "tester", "password": "wrong-password", "remember": False},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "用户名或密码错误"}
