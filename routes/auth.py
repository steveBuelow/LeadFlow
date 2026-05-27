from __future__ import annotations

import logging

from flask import Blueprint, request, session

from extensions import limiter
from models import (
    create_user,
    email_exists,
    find_user_by_credentials,
    find_user_by_id,
    update_last_login,
    username_exists,
)
from utils.security import clean, clean_email, err, generate_csrf, ok, require_csrf, validate_password, validate_username


auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


@auth_bp.get("/csrf")
def csrf():
    return ok({"csrf_token": generate_csrf()})


@auth_bp.post("/register")
@limiter.limit("5 per hour")
@require_csrf
def register():
    data = request.get_json(silent=True) or {}
    username = validate_username(data.get("username", ""))
    email = clean_email(data.get("email", ""))
    password = str(data.get("password", "") or "")

    if not username:
        return err("Username must be 3-32 characters using letters, numbers, hyphens, or underscores.")
    if not email:
        return err("A valid email address is required.")

    password_errors = validate_password(password)
    if password_errors:
        return err(password_errors[0])
    if username_exists(username):
        return err("That username is already taken.")
    if email_exists(email):
        return err("An account with that email already exists.")

    try:
        user_id = create_user(username, email, password)
    except Exception:
        logger.exception("Registration failed")
        return err("Could not create account. Please try again.", 500)

    session.clear()
    session["user_id"] = user_id
    session["username"] = username
    session.permanent = True
    return ok({"username": username, "message": f"Welcome, {username}!"}, 201)


@auth_bp.post("/login")
@limiter.limit("10 per hour")
@require_csrf
def login():
    data = request.get_json(silent=True) or {}
    login_value = clean(data.get("username", "") or data.get("login", ""), 254).lower()
    password = str(data.get("password", "") or "")
    if not login_value or not password:
        return err("Username/email and password are required.")

    user = find_user_by_credentials(login_value, password)
    if not user:
        return err("Invalid username or password.", 401)

    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session.permanent = True
    update_last_login(int(user["id"]))
    return ok({"username": user["username"], "email": user["email"]})


@auth_bp.post("/logout")
@require_csrf
def logout():
    session.clear()
    return ok({"message": "Signed out."})


@auth_bp.get("/me")
def me():
    user_id = session.get("user_id")
    if not user_id:
        return err("Not authenticated.", 401)
    user = find_user_by_id(int(user_id))
    if not user:
        session.clear()
        return err("User not found.", 401)
    return ok({"user": user, "csrf_token": generate_csrf()})
