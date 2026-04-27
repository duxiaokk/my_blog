from __future__ import annotations


def test_chat_api_route_removed(client):
    response = client.post("/api/chat", json={"user_message": "hello"})
    assert response.status_code == 404


def test_chat_route_not_registered():
    from main import app

    assert all(route.path != "/api/chat" for route in app.routes)
