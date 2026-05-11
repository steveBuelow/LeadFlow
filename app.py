import logging
import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify

from routes import register_routes

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def create_app() -> Flask:
    app = Flask(__name__)

    is_prod = os.getenv("FLASK_ENV") == "production"
    secret  = os.getenv("SECRET_KEY")

    if is_prod and not secret:
        raise RuntimeError("SECRET_KEY must be set in production")

    app.config["SECRET_KEY"]               = secret or "dev-secret-key"
    app.config["SESSION_PERMANENT"]        = True
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
    app.config.update(
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=is_prod,
        SESSION_COOKIE_HTTPONLY=True,
    )

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Route not found"}), 404

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify({"error": "Internal server error"}), 500

    register_routes(app)

    # ── Eagerly initialise DB pool so a bad DATABASE_URL blows up at startup,
    #    not silently on the first live request.
    with app.app_context():
        from db import init_pool
        init_pool()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_ENV") != "production")