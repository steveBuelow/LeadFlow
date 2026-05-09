from datetime import datetime, timedelta
import os
import random

import psycopg2
from flask import current_app, jsonify, render_template, request, session

from models import (
    create_user,
    create_lead,
    delete_lead,
    find_user,
    list_leads,
    update_lead,
)


def register_routes(app):
    def _is_prod() -> bool:
        return os.getenv("FLASK_ENV") == "production"

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
            return jsonify({"error": "User exists"}), 409
        except ValueError:
            return jsonify({"error": "Username and password are required"}), 400

    @app.route("/login", methods=["POST"])
    def login():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        result = find_user(username, password)
        if not result:
            return jsonify({"error": "Invalid login"}), 401

        session.permanent = True
        session["user_id"] = result["id"]
        session["username"] = result["username"]
        return jsonify({"status": "Logged in!"}), 200

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        return jsonify({"status": "Logged out!"}), 200

    @app.route("/me")
    def me():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not logged in"}), 401
        return jsonify({"username": session.get("username")}), 200

    # ── LEADS ─────────────────────────────────────────────
    @app.route("/leads")
    def get_leads():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401
        return jsonify({"leads": list_leads(user_id)}), 200

    @app.route("/add-lead", methods=["POST"])
    def add_lead():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401

        d = request.get_json(silent=True) or {}
        required = ["name", "source", "status"]
        missing = [field for field in required if not str(d.get(field, "")).strip()]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        try:
            new_id = create_lead(
                name=str(d["name"]).strip(),
                source=str(d["source"]).strip(),
                message=str(d.get("message", "")).strip(),
                status=str(d["status"]).strip(),
                notes=str(d.get("notes", "")).strip(),
                user_id=user_id,
            )
            return jsonify({"success": True, "id": new_id}), 201
        except Exception as e:
            current_app.logger.exception("Failed to create lead")
            if not _is_prod():
                return (
                    jsonify({"error": f"Failed to create lead: {type(e).__name__}: {e}"}),
                    500,
                )
            return jsonify({"error": "Failed to create lead"}), 500

    @app.route("/remove-lead", methods=["DELETE"])
    def remove_lead_route():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401

        d = request.get_json(silent=True) or {}
        lead_id = d.get("id", None)
        if lead_id is None:
            # allow /remove-lead?id=123 as a fallback
            lead_id = request.args.get("id", None)
        if lead_id is None or str(lead_id).strip() == "":
            return jsonify({"error": "Lead id is required"}), 400

        try:
            lead_id = int(lead_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Lead id must be an integer"}), 400

        try:
            deleted = delete_lead(lead_id, user_id)
        except Exception as e:
            current_app.logger.exception("Failed to delete lead")
            if not _is_prod():
                return (
                    jsonify({"error": f"Failed to delete lead: {type(e).__name__}: {e}"}),
                    500,
                )
            return jsonify({"error": "Failed to delete lead"}), 500
        if not deleted:
            return jsonify({"error": "Lead not found"}), 404
        return jsonify({"success": True}), 200

    @app.route("/update-lead", methods=["PUT"])
    def update_lead_route():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401

        d = request.get_json(silent=True) or {}
        required = ["id", "name", "source", "status"]
        missing = [
            field
            for field in required
            if field not in d or d[field] is None or str(d[field]).strip() == ""
        ]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        try:
            lead_id = int(d["id"])
        except (TypeError, ValueError):
            return jsonify({"error": "Lead id must be an integer"}), 400

        try:
            updated = update_lead(
                lead_id,
                user_id,
                str(d["name"]).strip(),
                str(d["source"]).strip(),
                str(d.get("message", "")).strip(),
                str(d["status"]).strip(),
                str(d.get("notes", "")).strip(),
            )
        except Exception as e:
            current_app.logger.exception("Failed to update lead")
            if not _is_prod():
                return (
                    jsonify({"error": f"Failed to update lead: {type(e).__name__}: {e}"}),
                    500,
                )
            return jsonify({"error": "Failed to update lead"}), 500
        if not updated:
            return jsonify({"error": "Lead not found"}), 404
        return jsonify({"success": True}), 200

    @app.route("/reminders")
    def get_reminders():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401

        seven_days_ago = datetime.now() - timedelta(days=7)

        # Using db.get_db() to avoid duplicating connection logic.
        from db import get_db  # local import to prevent circulars during boot
        from models import _jsonify_row  # local import; already used in list_leads

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, source, status, created_at
                    FROM leads
                    WHERE user_id = %s AND status = 'New' AND created_at <= %s
                    ORDER BY created_at ASC
                    """,
                    (user_id, seven_days_ago),
                )
                reminders = cur.fetchall()

        return jsonify({"reminders": [_jsonify_row(r) for r in reminders]}), 200

    @app.route("/generate-followup", methods=["POST"])
    def generate_followup():
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json(silent=True) or {}
        customer_name = (data.get("name") or "there").strip() or "there"
        original_msg = (data.get("message") or "your inquiry").strip() or "your inquiry"
        summary = (original_msg[:50] + "...") if len(original_msg) > 50 else original_msg

        templates = [
            f"Hi {customer_name},\n\nFollowing up on '{summary}'. Ready to take next steps?\n\nBest,",
            f"Hello {customer_name},\n\nChecking in on your interest in {summary}. We have openings next week!\n\nThanks!",
            f"Hi {customer_name},\n\nJust staying on your radar. Let me know if I can help!\n\nCheers,",
        ]
        return jsonify({"followup_text": random.choice(templates)}), 200
