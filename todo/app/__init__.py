#!/usr/bin/env python

import os
import logging
from flask import Flask, render_template, request
from flask_assets import Environment
from flask_ckeditor import CKEditor
from flask_compress import Compress
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_mail import Mail
from flask_msearch import Search
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_uploads import UploadSet, configure_uploads, IMAGES
from authlib.integrations.flask_client import OAuth
from config import config as Config
from app.common.tasks import msearch_celery_signal
from app.common.logs import init
from app.common.assets import app_css, app_js, vendor_css, vendor_js

# Initialize core extensions
db = SQLAlchemy()
csrf = CSRFProtect()
compress = Compress()
mail = Mail()
jwt = JWTManager()
search = Search()
socketio = SocketIO(logger=True, engineio_logger=True)
login_manager = LoginManager()

# Set up Flask-Login
login_manager.session_protection = "secure"
login_manager.login_view = "account.login"

# File upload sets
images = UploadSet("images", IMAGES)
docs = UploadSet("docs", ("rtf", "odf", "ods", "gnumeric", "abw", "doc", "docx", "xls", "xlsx", "pdf", "css"))

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

    # Register asset bundles
    configure_assets(app)

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    return app

def initialize_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    mail.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    compress.init_app(app)
    configure_uploads(app, images)
    configure_uploads(app, docs)
    CKEditor(app)
    OAuth(app)
    CORS(app, resources={r"/*": {"origins": app.config["ALLOWED_ORIGINS"]}})
    search.init_app(app)
    jwt.init_app(app)

    if not app.config["TESTING"]:
        socketio.server_options.update({"message_queue": app.config["REDIS_URL"]})
    socketio.init_app(app)

def configure_assets(app: Flask) -> None:
    """Configure Flask-Assets for managing CSS and JS."""
    assets_env = Environment(app)
    assets_env.url_expire = True
    asset_paths = ["assets/styles", "assets/scripts"]
    for path in asset_paths:
        assets_env.append_path(os.path.join(basedir, path))

    assets_env.register("app_css", app_css)
    assets_env.register("app_js", app_js)
    assets_env.register("vendor_css", vendor_css)
    assets_env.register("vendor_js", vendor_js)

def register_blueprints(app: Flask) -> None:
    """Register Flask blueprints."""
    from .blueprints.public import public as public_blueprint
    from .blueprints.tasks import content_manager as cont
    blueprints = [
        (public_blueprint, None),
        (content_manager_blueprint, None),
        (profile_blueprint, "/user"),
        (seeking_blueprint, "/preferences"),
        (messaging_manager_blueprint, "/message"),
        (notification_blueprint, "/notification"),
        (account_blueprint, "/account"),
        (photo_blueprint, "/photo"),
        (admin_blueprint, "/admin"),
        (search_blueprint, "/search"),
        (apis_blueprint, "/api"),
        (sitemaps, "/sitemaps"),
        (blog, "/blog"),
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

# SocketIO events
@socketio.on("connect")
def connect():
    from flask_login import current_user
    if current_user.is_authenticated:
        logger.info(f"User connected with socket id: {request.sid}")

@socketio.on("disconnect")
def disconnect():
    from flask_login import current_user
    if current_user.is_authenticated:
        logger.info(f"User disconnected with id: {request.sid}")

