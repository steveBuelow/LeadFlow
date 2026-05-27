from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def app(tmp_path: Path, monkeypatch):
    database_path = tmp_path / "leadflow-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("FLASK_ENV", "testing")

    from app import create_app

    return create_app({"TESTING": True})


@pytest.fixture()
def client(app):
    return app.test_client()


def issue_csrf(client) -> str:
    response = client.get("/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def register_and_login(
    client,
    username: str = "student_one",
    email: str = "student@example.com",
    password: str = "StrongPass1!",
):
    csrf = issue_csrf(client)
    response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201
    return response
