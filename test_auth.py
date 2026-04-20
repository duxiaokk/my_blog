from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
import models
import security


@pytest.fixture()
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with testing_session_local() as db:
        db.add(
            models.User(
                username="tester",
                email="tester@example.com",
                hashed_password=security.get_password_hash("correct-password"),
            )
        )
        db.commit()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_db, None)


def test_login_with_wrong_password_keeps_specific_error_message(client: TestClient):
    response = client.post(
        "/login",
        json={"username": "tester", "password": "wrong-password", "remember": False},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "\u7528\u6237\u540d\u6216\u5bc6\u7801\u9519\u8bef"}
