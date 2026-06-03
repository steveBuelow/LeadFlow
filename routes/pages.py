from flask import Blueprint, render_template


pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/")
def index():
    return render_template("index.html")


@pages_bp.get("/privacy")
def privacy():
    return render_template("privacy.html")


@pages_bp.get("/terms")
def terms():
    return render_template("terms.html")


@pages_bp.get("/contact")
def contact():
    return render_template("contact.html")


@pages_bp.get("/reset-password")
def reset_password_page():
    return render_template("reset_password.html")
