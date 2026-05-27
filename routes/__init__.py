from flask import Flask


def register_routes(app: Flask) -> None:
    from routes.ai import ai_bp
    from routes.auth import auth_bp
    from routes.leads import leads_bp
    from routes.pages import pages_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(leads_bp, url_prefix="/leads")
    app.register_blueprint(ai_bp, url_prefix="/ai")
