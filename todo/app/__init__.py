#!/usr/bin/env python

import logging
import os
from config import config as Config
from flask import Flask, render_template, request
from flask_compress import Compress
from flask_cors import CORS
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

# Initialize core extensions
db = SQLAlchemy()
csrf = CSRFProtect()
compress = Compress()
login_manager = LoginManager()

# Set up Flask-Login
login_manager.session_protection = "secure"
login_manager.login_view = "account.login"


# Base directory
basedir = os.path.abspath(os.path.dirname(__file__))

# Logger configuration
logger = logging.getLogger(__name__)

def create_app(config_name: str = None) -> Flask:
    """Create and configure the Flask app."""
    app = Flask(__name__)

    if config_name is None:
        config_name = os.getenv("FLASK_CONFIG", "default")
    app.config.from_object(Config[config_name])
    Config[config_name].init_app(app)

    # Set up extensions with the app context
    initialize_extensions(app)

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    return app

def initialize_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    compress.init_app(app)
    CORS(app, resources={r"/*": {"origins": app.config["ALLOWED_ORIGINS"]}})


def register_blueprints(app: Flask) -> None:
    """Register Flask blueprints."""
    from .blueprints.account import account as accounts
    from .blueprints.tasks import tasks
    blueprints = [
        (accounts, "/user"),
        (tasks, "/tasks"),
    ]

    for blueprint, url_prefix in blueprints:
        app.register_blueprint(blueprint, url_prefix=url_prefix)

def register_error_handlers(app: Flask) -> None:
    """Register error handlers for the Flask app."""
    @app.errorhandler(403)
    def forbidden(_):
        logger.warning("Forbidden access: 403")
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def page_not_found(_):
        logger.warning("Page not found: 404")
        return render_template("errors/404.html"), 404

    @app.errorhandler(400)
    def handle_bad_request(_):
        logger.error("Bad request: 400")
        return render_template("errors/400.html"), 400

    @app.errorhandler(500)
    def internal_server_error(_):
        logger.error("Internal server error: 500")
        return render_template("errors/500.html"), 500