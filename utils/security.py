from __future__ import annotations

import re
import secrets
from datetime import date
from functools import wraps
from html import unescape
from typing import Any, Callable

try:
    import bleach  # type: ignore
except ImportError:  # pragma: no cover - only used in limited envs
    bleach = None

try:
    from email_validator import EmailNotValidError, validate_email
except ImportError:  # pragma: no cover - only used in limited envs
    EmailNotValidError = ValueError
    validate_email = None

from flask import jsonify, request, session


CSRF_SESSION_KEY = "_csrf_token"
CSRF_HEADER = "X-CSRF-Token"
CSRF_COOKIE = "csrf_token"

STATUS_VALUES = ("New", "Contacted", "Qualified", "Proposal", "Closed-Won", "Closed-Lost")
PRIORITY_VALUES = ("low", "medium", "high")
SOURCE_MAX = 80
NAME_MAX = 120
EMAIL_MAX = 254
PHONE_MAX = 30
TEXT_MAX = 10_000
NOTE_MAX = 5_000
SUMMARY_MAX = 2_000


def generate_csrf() -> str:
    if CSRF_SESSION_KEY not in session:
        session[CSRF_SESSION_KEY] = secrets.token_hex(32)
    return str(session[CSRF_SESSION_KEY])


def validate_csrf() -> bool:
    token = (
        request.headers.get(CSRF_HEADER)
        or request.form.get("csrf_token")
        or ""
    ).strip()
    expected = str(session.get(CSRF_SESSION_KEY, "") or "")
    if not token or not expected:
        return False
    return secrets.compare_digest(token, expected)


def require_csrf(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not validate_csrf():
            return jsonify({"success": False, "error": "Invalid or missing CSRF token."}), 403
        return fn(*args, **kwargs)

    return wrapper


def login_required(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"success": False, "error": "Authentication required."}), 401
        return fn(*args, **kwargs)

    return wrapper


def clean(value: Any, max_length: int = 500) -> str:
    if not isinstance(value, str):
        value = "" if value is None else str(value)
    raw = unescape(value).replace("\x00", "")
    if bleach is not None:
        raw = bleach.clean(raw, tags=[], attributes={}, strip=True)
    else:  # pragma: no cover - only used when bleach is missing
        raw = re.sub(r"(?is)<[^>]*>", "", raw)
    raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw)
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = "\n".join(line.rstrip() for line in raw.split("\n"))
    return raw.strip()[:max_length]


def clean_email(value: Any) -> str:
    raw = clean(value, EMAIL_MAX).lower()
    if not raw:
        return ""
    if validate_email is not None:
        try:
            result = validate_email(raw, check_deliverability=False)
            return result.normalized
        except EmailNotValidError:
            return ""
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", raw):  # pragma: no cover
        return raw
    return ""


def clean_status(value: Any) -> str:
    raw = clean(value, 20)
    return raw if raw in STATUS_VALUES else ""


def clean_priority(value: Any) -> str:
    raw = clean(value, 10).lower()
    return raw if raw in PRIORITY_VALUES else ""


def clean_value(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        amount = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    if amount < 0:
        return None
    return round(amount, 2)


def validate_lead(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    name = clean(data.get("name", ""), NAME_MAX)
    if not name:
        errors.append("Contact name is required.")
    elif len(name) < 2:
        errors.append("Contact name must be at least 2 characters.")

    company = clean(data.get("company", ""), NAME_MAX) or None
    raw_email = clean(data.get("email", ""), EMAIL_MAX)
    email = clean_email(raw_email) if raw_email else None
    if raw_email and not email:
        errors.append("Email address is invalid.")

    phone = clean(data.get("phone", ""), PHONE_MAX) or None
    source = clean(data.get("source", "Manual"), SOURCE_MAX) or "Manual"

    raw_status = data.get("status", "New")
    status = clean_status(raw_status)
    if not status:
        errors.append("Status value is invalid.")
        status = "New"

    raw_priority = data.get("priority", "medium")
    priority = clean_priority(raw_priority)
    if not priority:
        errors.append("Priority value is invalid.")
        priority = "medium"

    message = clean(data.get("message", ""), TEXT_MAX) or None
    notes = clean(data.get("notes", ""), NOTE_MAX) or None
    deal_value = clean_value(data.get("value"))
    if data.get("value") not in (None, "", 0, "0", "0.00") and deal_value is None:
        errors.append("Deal value must be a valid non-negative amount.")

    followup_raw = clean(data.get("next_followup", ""), 12)
    next_followup: str | None = None
    if followup_raw:
        try:
            next_followup = date.fromisoformat(followup_raw).isoformat()
        except ValueError:
            errors.append("Follow-up date must use YYYY-MM-DD format.")

    cleaned = {
        "name": name,
        "company": company,
        "email": email,
        "phone": phone,
        "source": source,
        "status": status,
        "priority": priority,
        "value": deal_value,
        "message": message,
        "notes": notes,
        "next_followup": next_followup,
    }
    return cleaned, errors


def validate_username(value: Any) -> str | None:
    raw = clean(value, 32).lower()
    if re.fullmatch(r"[a-z0-9_-]{3,32}", raw):
        return raw
    return None


def validate_password(value: Any) -> list[str]:
    password = str(value or "")
    errors: list[str] = []
    if len(password) < 10:
        errors.append("Password must be at least 10 characters.")
    if len(password) > 72:
        errors.append("Password must not exceed 72 characters.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit.")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("Password must contain at least one special character.")
    return errors


def ok(data: dict[str, Any] | None = None, status: int = 200):
    payload = {"success": True}
    if data:
        payload.update(data)
    return jsonify(payload), status


def err(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status
