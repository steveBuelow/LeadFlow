from decimal import Decimal

from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db


def _jsonify_row(row: dict) -> dict:
    out = dict(row)
    for k, v in list(out.items()):
        if isinstance(v, Decimal):
            out[k] = float(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
    return out


def create_user(username, password):
    hashed_pw = generate_password_hash(password)
    with get_db() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, password) VALUES (%s, %s)",
                    (username, hashed_pw),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def find_user(username, password):
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


def get_user_by_id(user_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def create_lead(name, source, message, status, notes, user_id):
    with get_db() as conn:
        try:
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
        except Exception:
            conn.rollback()
            raise


def delete_lead(lead_id, user_id):
    with get_db() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM leads WHERE id = %s AND user_id = %s",
                    (lead_id, user_id),
                )
                deleted = cur.rowcount > 0
            conn.commit()
            return deleted
        except Exception:
            conn.rollback()
            raise


def update_lead(lead_id, user_id, name, source, message, status, notes):
    with get_db() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE leads
                    SET name = %s,
                        source = %s,
                        message = %s,
                        status = %s,
                        notes = %s
                    WHERE id = %s AND user_id = %s
                    """,
                    (name, source, message, status, notes, lead_id, user_id),
                )
                updated = cur.rowcount > 0
            conn.commit()
            return updated
        except Exception:
            conn.rollback()
            raise