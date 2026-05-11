import hashlib
import hmac
import os
from datetime import datetime, timedelta
from email.utils import parseaddr

import psycopg2
from flask import current_app, jsonify, render_template, request, session

from models import (
    create_lead,
    create_user,
    delete_lead,
    find_user,
    list_leads,
    update_lead,
    _jsonify_row,
)


# ── helpers ───────────────────────────────────────────────────────────────────


def _is_prod() -> bool:
    return os.getenv("FLASK_ENV") == "production"


def _require_login():
    """Return (user_id, None) or (None, error_response)."""
    uid = session.get("user_id")
    if not uid:
        return None, (jsonify({"error": "Unauthorized"}), 401)
    return uid, None


def _parse_int_id(value, field_name: str = "id"):
    """Parse an ID from request data; return (int, None) or (None, error_response)."""
    if value is None or str(value).strip() == "":
        return None, (jsonify({"error": f"{field_name} is required"}), 400)
    try:
        return int(value), None
    except (TypeError, ValueError):
        return None, (jsonify({"error": f"{field_name} must be an integer"}), 400)


def _verify_mailgun_sig(token: str, timestamp: str, signature: str) -> bool:
    """Return True if the Mailgun webhook signature is valid."""
    key = os.getenv("MAILGUN_SIGNING_KEY", "")
    if not key:
        return False
    expected = hmac.new(
        key.encode(),
        f"{timestamp}{token}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── route registration ────────────────────────────────────────────────────────


def register_routes(app):

    # ── INDEX ─────────────────────────────────────────────
    @app.route("/")
    def index():
        return render_template("index.html")

    # ── AUTH ──────────────────────────────────────────────
    @app.route("/signup", methods=["POST"])
    def signup():
        data = request.get_json(silent=True) or {}
        try:
            create_user(data.get("username"), data.get("password"))
            return jsonify({"message": "Account created!"}), 201
        except psycopg2.IntegrityError:
            return jsonify({"error": "Username already taken"}), 409
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/login", methods=["POST"])
    def login():
        data     = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        result = find_user(username, password)
        if not result:
            return jsonify({"error": "Invalid username or password"}), 401

        session.permanent          = True
        session["user_id"]         = result["id"]
        session["username"]        = result["username"]
        return jsonify({"status": "ok"}), 200

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        return jsonify({"status": "ok"}), 200

    @app.route("/me")
    def me():
        if not session.get("user_id"):
            return jsonify({"error": "Not logged in"}), 401
        return jsonify({"username": session["username"]}), 200

    # ── LEADS ─────────────────────────────────────────────
    @app.route("/leads")
    def get_leads():
        user_id, err = _require_login()
        if err:
            return err
        return jsonify({"leads": list_leads(user_id)}), 200

    @app.route("/add-lead", methods=["POST"])
    def add_lead():
        user_id, err = _require_login()
        if err:
            return err

        d = request.get_json(silent=True) or {}

        # ── FIX: source is required on backend; frontend now validates it too.
        #         Provide a clear, field-specific error message so the client
        #         can show it directly rather than a generic "Missing fields".
        name   = str(d.get("name",   "")).strip()
        source = str(d.get("source", "")).strip()
        status = str(d.get("status", "")).strip()

        errors = []
        if not name:   errors.append("Contact name is required.")
        if not source: errors.append("Source is required (e.g. Referral, Website).")
        if not status: errors.append("Status is required.")
        if errors:
            return jsonify({"error": " ".join(errors)}), 400

        try:
            new_id = create_lead(
                name=name,
                source=source,
                message=str(d.get("message", "")).strip(),
                status=status,
                notes=str(d.get("notes", "")).strip(),
                user_id=user_id,
            )
            return jsonify({"success": True, "id": new_id}), 201
        except Exception:
            current_app.logger.exception("Failed to create lead")
            msg = "Failed to create lead"
            return jsonify({"error": msg}), 500

    @app.route("/remove-lead", methods=["DELETE"])
    def remove_lead_route():
        user_id, err = _require_login()
        if err:
            return err

        d = request.get_json(silent=True) or {}
        raw_id = d.get("id") or request.args.get("id")

        lead_id, err = _parse_int_id(raw_id)
        if err:
            return err

        try:
            deleted = delete_lead(lead_id, user_id)
        except Exception:
            current_app.logger.exception("Failed to delete lead %s", lead_id)
            return jsonify({"error": "Failed to delete lead"}), 500

        if not deleted:
            return jsonify({"error": "Lead not found"}), 404
        return jsonify({"success": True}), 200

    @app.route("/update-lead", methods=["PUT"])
    def update_lead_route():
        user_id, err = _require_login()
        if err:
            return err

        d = request.get_json(silent=True) or {}

        # ── FIX: validate required fields with clear messages ──
        name   = str(d.get("name",   "")).strip()
        source = str(d.get("source", "")).strip()
        status = str(d.get("status", "")).strip()

        errors = []
        if not name:   errors.append("Contact name is required.")
        if not source: errors.append("Source is required.")
        if not status: errors.append("Status is required.")
        if errors:
            return jsonify({"error": " ".join(errors)}), 400

        lead_id, err = _parse_int_id(d.get("id"))
        if err:
            return err

        try:
            updated = update_lead(
                lead_id,
                user_id,
                name,
                source,
                str(d.get("message", "")).strip(),
                status,
                str(d.get("notes", "")).strip(),
            )
        except Exception:
            current_app.logger.exception("Failed to update lead %s", lead_id)
            return jsonify({"error": "Failed to update lead"}), 500

        if not updated:
            return jsonify({"error": "Lead not found"}), 404
        return jsonify({"success": True}), 200

    # ── REMINDERS ─────────────────────────────────────────
    @app.route("/reminders")
    def get_reminders():
        user_id, err = _require_login()
        if err:
            return err

        seven_days_ago = datetime.now() - timedelta(days=7)

        from db import get_db
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, source, status, created_at
                    FROM   leads
                    WHERE  user_id = %s
                      AND  status  = 'New'
                      AND  created_at <= %s
                    ORDER  BY created_at ASC
                    """,
                    (user_id, seven_days_ago),
                )
                rows = cur.fetchall()

        return jsonify({"reminders": [_jsonify_row(r) for r in rows]}), 200

    # ── FOLLOW-UP GENERATOR ───────────────────────────────
    @app.route("/generate-followup", methods=["POST"])
    def generate_followup():
        user_id, err = _require_login()
        if err:
            return err

        data          = request.get_json(silent=True) or {}
        customer_name = (data.get("name")    or "there").strip() or "there"
        original_msg  = (data.get("message") or "your inquiry").strip() or "your inquiry"
        summary       = (original_msg[:50] + "…") if len(original_msg) > 50 else original_msg

        import random
        templates = [
            f"Hi {customer_name},\n\nFollowing up on \"{summary}\" — are you ready to take the next step? Happy to jump on a quick call.\n\nBest,",
            f"Hello {customer_name},\n\nJust checking in on your interest regarding {summary}. We have availability next week if you'd like to connect!\n\nThanks!",
            f"Hi {customer_name},\n\nWanted to stay on your radar! If you have any questions about {summary}, I'm here to help.\n\nCheers,",
        ]
        return jsonify({"followup_text": random.choice(templates)}), 200

    # ── INBOUND EMAIL → LEAD ──────────────────────────────
    #
    #  Set up Mailgun (or any service that POSTs parsed email) to forward
    #  inbound mail to:  POST /inbound-email
    #
    #  Required env vars:
    #    MAILGUN_SIGNING_KEY  — your Mailgun webhook signing key (Settings → Webhooks)
    #    INBOUND_USER_ID      — the user_id that inbound leads are assigned to
    #
    #  Mailgun inbound route expression:
    #    match_recipient("leads@yourdomain.com")
    #  Action:
    #    forward("https://yourapp.com/inbound-email")
    #
    @app.route("/inbound-email", methods=["POST"])
    def inbound_email():
        # ── 1. Verify Mailgun signature ─────────────────────
        signing_key = os.getenv("MAILGUN_SIGNING_KEY")
        if signing_key:
            token     = request.form.get("token",     "")
            timestamp = request.form.get("timestamp", "")
            signature = request.form.get("signature", "")
            if not _verify_mailgun_sig(token, timestamp, signature):
                current_app.logger.warning("Inbound email: invalid Mailgun signature")
                return jsonify({"error": "Invalid signature"}), 403
        else:
            # Warn loudly in logs; don't block (lets you test locally without a key).
            current_app.logger.warning(
                "MAILGUN_SIGNING_KEY not set — inbound-email endpoint is unauthenticated!"
            )

        # ── 2. Parse sender ─────────────────────────────────
        from_raw              = request.form.get("from", "")
        sender_name, sender_email = parseaddr(from_raw)
        sender_name = (sender_name or sender_email or "").strip()

        if not sender_name:
            return jsonify({"error": "Could not parse sender from email"}), 400

        subject = request.form.get("subject",    "").strip()
        body    = request.form.get("body-plain", "").strip()

        # Build the message shown in the CRM
        if subject and body:
            message = f"Subject: {subject}\n\n{body}"
        elif subject:
            message = f"Subject: {subject}"
        else:
            message = body

        # ── 3. Resolve which user to assign the lead to ─────
        raw_uid = os.getenv("INBOUND_USER_ID", "")
        if not raw_uid:
            current_app.logger.error("INBOUND_USER_ID env var is not set")
            return jsonify({"error": "Server not configured for inbound email"}), 500

        try:
            inbound_user_id = int(raw_uid)
        except ValueError:
            current_app.logger.error("INBOUND_USER_ID must be an integer, got: %r", raw_uid)
            return jsonify({"error": "Server misconfiguration"}), 500

        # ── 4. Create the lead ──────────────────────────────
        try:
            new_id = create_lead(
                name=sender_name,
                source="Email",
                message=message,
                status="New",
                notes=f"Inbound email from {sender_email}",
                user_id=inbound_user_id,
            )
            current_app.logger.info(
                "Inbound email → lead #%d  from=%s", new_id, sender_email
            )
            return jsonify({"success": True, "id": new_id}), 201
        except Exception:
            current_app.logger.exception("Failed to create lead from inbound email")
            return jsonify({"error": "Failed to process email"}), 500