"""
MindGuardian AI — Application Factory
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect

from app.config import config_map

# ---------------------------------------------------------------------------
# Extension instances (initialised without an app — bound in create_app)
# ---------------------------------------------------------------------------
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()


def create_app(env: str | None = None) -> Flask:
    """Application factory.  Call with no args for the default (dev) config."""

    env = env or os.environ.get("FLASK_ENV", "default")
    cfg = config_map.get(env, config_map["default"])

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(cfg)

    # Ensure the instance folder exists so SQLite can write there
    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)

    # ------------------------------------------------------------------
    # Bind extensions
    # ------------------------------------------------------------------
    db.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"          # redirect target
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    # ------------------------------------------------------------------
    # Register blueprints
    # ------------------------------------------------------------------
    from app.auth.routes import auth_bp
    from app.main.routes import main_bp
    from app.chat.routes import chat_bp
    from app.mood.routes import mood_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(mood_bp, url_prefix="/mood")

    # ------------------------------------------------------------------
    # Create all DB tables on first run
    # ------------------------------------------------------------------
    with app.app_context():
        db.create_all()

    return app
