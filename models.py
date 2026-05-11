from decimal import Decimal

from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db


def _jsonify_row(row: dict) -> dict:
    """Convert psycopg2/Decimal/datetime values into JSON-safe primitives."""
    out = dict(row)
    for k, v in list(out.items()):
        if isinstance(v, Decimal):
            out[k] = float(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
    return out


# ── USERS ─────────────────────────────────────────────────────────────────────


def create_user(username: str, password: str) -> None:
    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        raise ValueError("Username and password are required")

    hashed = generate_password_hash(password)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed),
            )
        conn.commit()
    # IntegrityError (duplicate username) is intentionally NOT caught here;
    # it bubbles up to the route which returns a 409.


def find_user(username: str, password: str) -> dict | None:
    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        return None

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, password FROM users WHERE username = %s",
                (username,),
            )
            user = cur.fetchone()

    if user and check_password_hash(user["password"], password):
        return {"id": user["id"], "username": user["username"]}
    return None


def get_user_by_id(user_id: int) -> dict | None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
    return dict(row) if row else None


# ── LEADS ─────────────────────────────────────────────────────────────────────


def list_leads(user_id: int) -> list[dict]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, source, message, status, notes, created_at
                FROM   leads
                WHERE  user_id = %s
                ORDER  BY created_at DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
    return [_jsonify_row(r) for r in rows]


def create_lead(
    name: str,
    source: str,
    message: str,
    status: str,
    notes: str,
    user_id: int,
) -> int:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO leads (name, source, message, status, notes, user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (name, source, message, status, notes, user_id),
            )
            new_id = cur.fetchone()["id"]
        conn.commit()
    return new_id


def delete_lead(lead_id: int, user_id: int) -> bool:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM leads WHERE id = %s AND user_id = %s",
                (lead_id, user_id),
            )
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted


def update_lead(
    lead_id: int,
    user_id: int,
    name: str,
    source: str,
    message: str,
    status: str,
    notes: str,
) -> bool:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE leads
                SET  name    = %s,
                     source  = %s,
                     message = %s,
                     status  = %s,
                     notes   = %s
                WHERE id = %s AND user_id = %s
                """,
                (name, source, message, status, notes, lead_id, user_id),
            )
            updated = cur.rowcount > 0
        conn.commit()
    return updated