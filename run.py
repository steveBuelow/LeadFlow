"""
Development entry point.
In production, use: gunicorn -w 4 -b 0.0.0.0:5000 "run:app"
"""

import os

from app import app


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=(os.environ.get("FLASK_ENV") or "development").lower() != "production",
    )
