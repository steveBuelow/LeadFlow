from datetime import datetime, timedelta
import random

import psycopg2
from flask import jsonify, render_template, request, session

from db import get_db
from models import (
    _jsonify_row,
    create_user,
    find_user,
    create_lead,
    delete_lead,
    update_lead,
)


def register_routes(app):
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/signup", methods=["POST"])
    def signup():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        try:
            create_user(username, password)
            return jsonify({"message": "Account created!"}), 201
        except psycopg2.IntegrityError:
            return jsonify({"error": "User exists"}), 409

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

    @app.route("/leads")
    def get_leads():
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM leads WHERE user_id = %s ORDER BY created_at DESC",
                    (session["user_id"],),
                )
                rows = cur.fetchall()

        return jsonify({"leads": [_jsonify_row(r) for r in rows]}), 200

    @app.route("/add-lead", methods=["POST"])
    def add_lead():
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401

        d = request.get_json(silent=True) or {}
        
        # 1. Validation Logic
        required = ["name", "source", "status"]
        missing = [field for field in required if not str(d.get(field, "")).strip()]

        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        try:
            # 2. Safe Data Retrieval
            # Use .get() for 'message' in case it's optional/missing from the JSON
            new_id = create_lead(
                d["name"].strip(),
                d["source"].strip(),
                d.get("message", "").strip(),  # Changed from d["message"]
                d["status"].strip(),
                session["user_id"],
                notes=d.get("notes", "").strip()
            )
            return jsonify({"success": True, "id": new_id}), 201
            
        except Exception as e:
            # 3. Debugging Tip
            print(f"Error creating lead: {e}") # This helps you see the actual error in Render logs
            return jsonify({"error": "Failed to create lead"}), 500

    @app.route("/remove-lead", methods=["DELETE"])
    def remove_lead_route():
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401

        d = request.get_json(silent=True) or {}
        lead_id = d.get("id")
        if lead_id is None:
            return jsonify({"error": "Lead id is required"}), 400

        deleted = delete_lead(lead_id, session["user_id"])
        if not deleted:
            return jsonify({"error": "Lead not found"}), 404

        return jsonify({"success": True}), 200

    @app.route("/reminders")
    def get_reminders():
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401

        seven_days_ago = datetime.now() - timedelta(days=7)

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, source, status, created_at
                    FROM leads
                    WHERE user_id = %s AND status = 'New' AND created_at <= %s
                    ORDER BY created_at ASC
                    """,
                    (session["user_id"], seven_days_ago),
                )
                reminders = cur.fetchall()

        return jsonify({"reminders": [_jsonify_row(r) for r in reminders]}), 200

    @app.route("/update-lead", methods=["PUT"])
    def update_lead_route():
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401

        d = request.get_json(silent=True) or {}
        required = ["id", "name", "source", "status",]
        missing = [
            field for field in required
            if field not in d or d[field] is None or str(d[field]).strip() == ""
        ]

        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        updated = update_lead(
            d["id"],
            session["user_id"],
            d["name"].strip(),
            d["source"].strip(),
            d["message"].strip(),
            d["status"].strip(),
            d["notes"].strip(),
        )

        if not updated:
            return jsonify({"error": "Lead not found"}), 404

        return jsonify({"success": True}), 200

    @app.route("/generate-followup", methods=["POST"])
    def generate_followup():
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401   # ← guard first

        data = request.get_json(silent=True) or {}
        customer_name = (data.get("name") or "there").strip() or "there"
        original_msg  = (data.get("message") or "your inquiry").strip() or "your inquiry"
        summary       = (original_msg[:50] + "...") if len(original_msg) > 50 else original_msg

        templates = [
            f"Hi {customer_name},\n\nFollowing up on '{summary}'. Ready to take next steps?\n\nBest,",
            f"Hello {customer_name},\n\nChecking in on your interest in {summary}. We have openings next week!\n\nThanks!",
            f"Hi {customer_name},\n\nJust staying on your radar. Let me know if I can help!\n\nCheers,",
        ]
        return jsonify({"followup_text": random.choice(templates)}), 200