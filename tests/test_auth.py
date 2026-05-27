from __future__ import annotations

from conftest import issue_csrf, register_and_login


def test_index_renders_spa_shell(client):
    response = client.get("/")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "LeadFlow" in body
    assert "Pipeline command center" in body


def test_missing_csrf_rejected_on_register(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "student_one",
            "email": "student@example.com",
            "password": "StrongPass1!",
        },
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "Invalid or missing CSRF token."


def test_register_me_logout_flow(client):
    register_and_login(client)

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.get_json()["user"]["username"] == "student_one"

    csrf = issue_csrf(client)
    logout = client.post("/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 200

    me_after = client.get("/auth/me")
    assert me_after.status_code == 401


def test_duplicate_username_and_email_rejected(client):
    register_and_login(client)
    csrf = issue_csrf(client)

    dup_username = client.post(
        "/auth/register",
        json={
            "username": "student_one",
            "email": "other@example.com",
            "password": "StrongPass1!",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert dup_username.status_code == 400
    assert "already taken" in dup_username.get_json()["error"]

    csrf = issue_csrf(client)
    dup_email = client.post(
        "/auth/register",
        json={
            "username": "student_two",
            "email": "student@example.com",
            "password": "StrongPass1!",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert dup_email.status_code == 400
    assert "already exists" in dup_email.get_json()["error"]


def test_security_headers_and_cookie_attributes(client):
    response = client.get("/")
    assert response.headers["Content-Security-Policy"].startswith("default-src 'self'")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    auth_response = register_and_login(client, username="cookie_user", email="cookie@example.com")
    cookie_values = auth_response.headers.getlist("Set-Cookie")
    assert any("SameSite=Strict" in cookie for cookie in cookie_values)
    assert any("HttpOnly" in cookie for cookie in cookie_values)


def test_session_cookie_has_secure_flags_in_production_config(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "prod-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/leadflow-prod-test.db")

    from app import create_app

    app = create_app({"TESTING": True})
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Strict"
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_NAME"] == "__Host-leadflow-sid"


def test_invalid_password_rejected(client):
    csrf = issue_csrf(client)
    response = client.post(
        "/auth/register",
        json={
            "username": "weak_user",
            "email": "weak@example.com",
            "password": "weak",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 400
    assert "at least 10 characters" in response.get_json()["error"]
