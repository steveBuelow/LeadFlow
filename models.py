from __future__ import annotations

import hashlib
import secrets as _secrets
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

try:
    import bcrypt  # type: ignore
except ImportError:  # pragma: no cover - only used in limited envs
    bcrypt = None
    from werkzeug.security import check_password_hash, generate_password_hash

from db import fetch_all, fetch_one, get_db, insert_returning_id, is_sqlite_url, execute_write


if bcrypt is not None:
    _DUMMY_HASH = bcrypt.hashpw(b"not-the-password", bcrypt.gensalt(rounds=12))
else:  # pragma: no cover - only used when bcrypt is missing
    _DUMMY_HASH = generate_password_hash("not-the-password")


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def utc_now_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def _jsonify_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            out[key] = float(value)
        elif isinstance(value, datetime):
            out[key] = value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        elif isinstance(value, date):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    raw = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)


def _hash_password(password: str) -> str:
    if bcrypt is not None:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=13)).decode("utf-8")
    return generate_password_hash(password, method="pbkdf2:sha256:600000")  # pragma: no cover


def _verify_password(password: str, password_hash: str) -> bool:
    if bcrypt is not None:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except Exception:
            return False
    return check_password_hash(password_hash, password)  # pragma: no cover


def create_user(username: str, email: str, password: str) -> int:
    return insert_returning_id(
        """
        INSERT INTO users (username, email, password, created_at, is_active)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (username, email, _hash_password(password), utc_now_iso(), True),
    )


def find_user_by_credentials(login: str, password: str) -> dict[str, Any] | None:
    row = fetch_one(
        """
        SELECT id, username, email, password
        FROM users
        WHERE (username = %s OR email = %s) AND is_active = TRUE
        LIMIT 1
        """,
        (login, login),
    )

    if bcrypt is not None:
        stored = row["password"].encode("utf-8") if row else _DUMMY_HASH
        try:
            matched = bcrypt.checkpw(password.encode("utf-8"), stored)
        except Exception:
            matched = False
    else:  # pragma: no cover
        stored = row["password"] if row else _DUMMY_HASH
        matched = check_password_hash(stored, password)

    if row and matched:
        return {"id": int(row["id"]), "username": str(row["username"]), "email": str(row["email"])}
    return None


def find_user_by_id(user_id: int) -> dict[str, Any] | None:
    row = fetch_one(
        """
        SELECT id, username, email, last_login, created_at
        FROM users
        WHERE id = %s AND is_active = TRUE
        LIMIT 1
        """,
        (user_id,),
    )
    return _jsonify_row(row) if row else None


def update_last_login(user_id: int) -> None:
    execute_write(
        "UPDATE users SET last_login = %s WHERE id = %s",
        (utc_now_iso(), user_id),
    )

def username_exists(username: str) -> bool:
    return fetch_one("SELECT 1 AS found FROM users WHERE username = %s LIMIT 1", (username,)) is not None


def email_exists(email: str) -> bool:
    return fetch_one("SELECT 1 AS found FROM users WHERE email = %s LIMIT 1", (email,)) is not None


_LEAD_COLUMNS = """
    id, user_id, name, company, email, phone, source, status, priority,
    value, message, notes, next_followup, ai_score, ai_summary, ai_category,
    created_at, updated_at
"""


def list_leads(user_id: int, status: str | None = None) -> list[dict[str, Any]]:
    params: list[Any] = [user_id]
    query = f"SELECT {_LEAD_COLUMNS} FROM leads WHERE user_id = %s"
    if status and status != "All":
        query += " AND status = %s"
        params.append(status)
    query += " ORDER BY created_at DESC, id DESC"
    rows = fetch_all(query, tuple(params))
    return [_jsonify_row(row) for row in rows]


def get_lead(lead_id: int, user_id: int) -> dict[str, Any] | None:
    row = fetch_one(
        f"SELECT {_LEAD_COLUMNS} FROM leads WHERE id = %s AND user_id = %s LIMIT 1",
        (lead_id, user_id),
    )
    return _jsonify_row(row) if row else None


def create_lead(data: dict[str, Any], user_id: int) -> int:
    now = utc_now_iso()
    return insert_returning_id(
        """
        INSERT INTO leads (
            user_id, name, company, email, phone, source, status, priority,
            value, message, notes, next_followup, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            data["name"],
            data.get("company"),
            data.get("email"),
            data.get("phone"),
            data.get("source"),
            data.get("status"),
            data.get("priority"),
            data.get("value"),
            data.get("message"),
            data.get("notes"),
            data.get("next_followup"),
            now,
            now,
        ),
    )


def update_lead(lead_id: int, user_id: int, data: dict[str, Any]) -> bool:
    updated = execute_write(
        """
        UPDATE leads SET
            name = %s,
            company = %s,
            email = %s,
            phone = %s,
            source = %s,
            status = %s,
            priority = %s,
            value = %s,
            message = %s,
            notes = %s,
            next_followup = %s,
            updated_at = %s
        WHERE id = %s AND user_id = %s
        """,
        (
            data["name"],
            data.get("company"),
            data.get("email"),
            data.get("phone"),
            data.get("source"),
            data.get("status"),
            data.get("priority"),
            data.get("value"),
            data.get("message"),
            data.get("notes"),
            data.get("next_followup"),
            utc_now_iso(),
            lead_id,
            user_id,
        ),
    )
    return updated > 0


def update_lead_status(lead_id: int, user_id: int, status: str) -> bool:
    updated = execute_write(
        "UPDATE leads SET status = %s, updated_at = %s WHERE id = %s AND user_id = %s",
        (status, utc_now_iso(), lead_id, user_id),
    )
    return updated > 0


def delete_lead(lead_id: int, user_id: int) -> bool:
    return execute_write("DELETE FROM leads WHERE id = %s AND user_id = %s", (lead_id, user_id)) > 0


def lead_stats(user_id: int) -> dict[str, Any]:
    leads = list_leads(user_id)
    total = len(leads)
    new_count = sum(1 for lead in leads if lead["status"] == "New")
    qualified = sum(1 for lead in leads if lead["status"] == "Qualified")
    closed_won = [lead for lead in leads if lead["status"] == "Closed-Won"]
    closed_lost = [lead for lead in leads if lead["status"] == "Closed-Lost"]
    pipeline_total = round(sum(float(lead.get("value") or 0) for lead in leads), 2)
    pipeline_won = round(sum(float(lead.get("value") or 0) for lead in closed_won), 2)
    added_this_week = 0
    overdue = 0
    now = utc_now()

    for lead in leads:
        created_at = _parse_dt(lead.get("created_at"))
        if created_at and created_at >= now - timedelta(days=7):
            added_this_week += 1
        followup = lead.get("next_followup")
        if followup and lead["status"] not in {"Closed-Won", "Closed-Lost"}:
            try:
                followup_date = date.fromisoformat(str(followup))
            except ValueError:
                continue
            if followup_date <= now.date():
                overdue += 1

    won_rate = round((len(closed_won) / total) * 100, 1) if total else 0.0
    return {
        "total": total,
        "new_count": new_count,
        "qualified": qualified,
        "closed_won": len(closed_won),
        "closed_lost": len(closed_lost),
        "pipeline_total": pipeline_total,
        "pipeline_won": pipeline_won,
        "added_this_week": added_this_week,
        "overdue_followups": overdue,
        "won_rate": won_rate,
    }


def stale_leads(user_id: int, days: int = 7) -> list[dict[str, Any]]:
    threshold = utc_now() - timedelta(days=days)
    results: list[dict[str, Any]] = []
    for lead in list_leads(user_id, status="New"):
        created_at = _parse_dt(lead.get("created_at"))
        if created_at and created_at < threshold:
            results.append({
                "id": lead["id"],
                "name": lead["name"],
                "source": lead.get("source"),
                "created_at": lead.get("created_at"),
            })
    return results[:20]


def overdue_followups(user_id: int) -> list[dict[str, Any]]:
    today = utc_now().date()
    results: list[dict[str, Any]] = []
    for lead in list_leads(user_id):
        if lead["status"] in {"Closed-Won", "Closed-Lost"} or not lead.get("next_followup"):
            continue
        try:
            followup_date = date.fromisoformat(str(lead["next_followup"]))
        except ValueError:
            continue
        if followup_date <= today:
            results.append({
                "id": lead["id"],
                "name": lead["name"],
                "next_followup": lead["next_followup"],
                "status": lead["status"],
            })
    results.sort(key=lambda row: row["next_followup"])
    return results[:20]


def update_ai_fields(
    lead_id: int,
    user_id: int,
    score: int | None = None,
    summary: str | None = None,
    category: str | None = None,
) -> bool:
    updated = execute_write(
        """
        UPDATE leads SET
            ai_score = COALESCE(%s, ai_score),
            ai_summary = COALESCE(%s, ai_summary),
            ai_category = COALESCE(%s, ai_category),
            updated_at = %s
        WHERE id = %s AND user_id = %s
        """,
        (score, summary, category, utc_now_iso(), lead_id, user_id),
    )
    return updated > 0


# ── Password Reset ─────────────────────────────────────────────────────────

def _hash_token(token: str) -> str:
    """SHA-256 hash of a raw token — safe to store in DB."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def find_user_by_email(email: str) -> dict[str, Any] | None:
    row = fetch_one(
        "SELECT id, username, email FROM users WHERE email = %s AND is_active = TRUE LIMIT 1",
        (email,),
    )
    return dict(row) if row else None


def create_reset_token(user_id: int) -> str:
    """Generate a secure reset token, store its hash, and return the raw token."""
    # Invalidate any previous unused tokens for this user first
    execute_write(
        "DELETE FROM password_resets WHERE user_id = %s AND used_at IS NULL",
        (user_id,),
    )
    token = _secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    expires_at = (utc_now() + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    insert_returning_id(
        """
        INSERT INTO password_resets (user_id, token_hash, expires_at, created_at)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, token_hash, expires_at, utc_now_iso()),
    )
    return token


def verify_reset_token(token: str) -> dict[str, Any] | None:
    """Return the reset row if the token is valid, unexpired, and unused; else None."""
    token_hash = _hash_token(token)
    row = fetch_one(
        "SELECT id, user_id, expires_at, used_at FROM password_resets WHERE token_hash = %s LIMIT 1",
        (token_hash,),
    )
    if not row:
        return None
    if row.get("used_at"):
        return None
    expires_at = _parse_dt(row.get("expires_at"))
    if not expires_at or utc_now() > expires_at:
        return None
    return _jsonify_row(row)


def consume_reset_token(token_id: int, user_id: int, new_password: str) -> bool:
    """Mark the token used and update the user password in a single transaction."""
    new_hash = _hash_password(new_password)
    now = utc_now_iso()
    ph = "?" if is_sqlite_url() else "%s"

    with get_db() as conn:
        cur = conn.cursor()
        try:
            # Mark token used — if rowcount is 0, it was already consumed
            cur.execute(
                f"UPDATE password_resets SET used_at = {ph} WHERE id = {ph} AND used_at IS NULL",
                (now, token_id),
            )
            if cur.rowcount == 0:
                return False
            # Update password
            cur.execute(
                f"UPDATE users SET password = {ph} WHERE id = {ph} AND is_active = TRUE",
                (new_hash, user_id),
            )
            return cur.rowcount > 0
        finally:
            cur.close()
