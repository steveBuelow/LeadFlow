from __future__ import annotations

import logging
import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify

from db import close_pool, init_pool, init_schema
from utils.security import generate_csrf
from extensions import limiter


load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def create_app(config_override: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    env_name = (os.environ.get("FLASK_ENV") or "development").strip().lower()
    is_production = env_name == "production"
    configured_secret = os.environ.get("SECRET_KEY")
    if is_production and not configured_secret:
        raise RuntimeError("SECRET_KEY must be set in production.")

    cookie_secure = is_production or os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    cookie_name = "__Host-leadflow-sid" if cookie_secure else "leadflow-sid"

    app.config.update(
        APP_NAME="LeadFlow",
        DATABASE_URL=os.environ.get("DATABASE_URL", "sqlite:///instance/leadflow.db"),
        SECRET_KEY=configured_secret or "dev-secret-key-NOT-for-production",
        SESSION_PERMANENT=True,
        PERMANENT_SESSION_LIFETIME=timedelta(days=int(os.environ.get("SESSION_LIFETIME_DAYS", 7))),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=cookie_secure,
        SESSION_COOKIE_NAME=cookie_name,
        SESSION_COOKIE_PATH="/",
        TESTING=False,
        JSON_SORT_KEYS=False,
        MAX_CONTENT_LENGTH=256 * 1024,
    )
    if config_override:
        app.config.update(config_override)

    limiter.init_app(app)

    init_schema()
    if not app.config.get("TESTING"):
        try:
            init_pool()
        except Exception as exc:  # pragma: no cover - depends on external DB availability
            logger.warning("DB pool init deferred: %s", exc)

    @app.after_request
    def set_security_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "object-src 'none'"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=()"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        if is_production:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

        token = generate_csrf()
        response.set_cookie(
            "csrf_token",
            token,
            httponly=False,
            secure=cookie_secure,
            samesite="Strict",
            max_age=3600,
            path="/",
        )
        return response

    from routes import register_routes

    register_routes(app)

    @app.get("/healthz")
    def healthz():
        return jsonify({"ok": True, "app": app.config["APP_NAME"]})

    @app.get("/healthz/db")
    def healthz_db():
        """
        Safe DB connectivity diagnostic — never exposes credentials or stack traces.
        Returns error type + message so you can diagnose RLS / SSL / connection issues
        without leaking secrets. Blocked in production.
        """
        if is_production:
            return jsonify({"ok": False, "error": "Not available in production."}), 403
        try:
            from db import fetch_one as _fetch
            result = _fetch("SELECT current_user AS u, pg_backend_pid() AS pid")
            # Also test INSERT privilege by checking RLS status on the users table
            rls_row = _fetch(
                "SELECT relrowsecurity AS rls_enabled "
                "FROM pg_class WHERE relname = 'users' AND relnamespace = 'public'::regnamespace"
            )
            return jsonify({
                "ok": True,
                "db_user": result.get("u") if result else None,
                "backend_pid": result.get("pid") if result else None,
                "users_rls_enabled": rls_row.get("rls_enabled") if rls_row else None,
            })
        except Exception as exc:
            # Expose error TYPE + message only — no secrets, no traceback
            return jsonify({
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
            }), 500

    @app.errorhandler(400)
    def bad_request(_error):
        return jsonify({"success": False, "error": "Bad request."}), 400

    @app.errorhandler(401)
    def unauthorized(_error):
        return jsonify({"success": False, "error": "Authentication required."}), 401

    @app.errorhandler(403)
    def forbidden(_error):
        return jsonify({"success": False, "error": "Forbidden."}), 403

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"success": False, "error": "Not found."}), 404

    @app.errorhandler(429)
    def rate_limited(_error):
        return jsonify({"success": False, "error": "Too many requests. Slow down!"}), 429

    @app.errorhandler(500)
    def server_error(_error):
        logger.exception("Unhandled 500")
        return jsonify({"success": False, "error": "Internal server error."}), 500

    @app.teardown_appcontext
    def _teardown(_exc):
        if app.config.get("TESTING"):
            close_pool()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_ENV") != "production")
