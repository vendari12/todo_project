import os
import sys
import logging

import eventlet
from dotenv import load_dotenv
from eventlet.green import urllib

# Apply eventlet monkey patch
eventlet.monkey_patch()

# Load environment variables from .env file
load_dotenv()

# Determine Python version and handle imports accordingly
PYTHON_VERSION = sys.version_info[0]
if PYTHON_VERSION == 3:
    import urllib.parse as urlparse
else:
    import urlparse

# Base directory of the application
basedir = os.path.abspath(os.path.dirname(__file__))

def get_env_variable(name, default=None, cast_type=str):
    """Helper function to retrieve environment variables with type casting."""
    value = os.environ.get(name, default)
    if value is not None:
        try:
            value = cast_type(value)
        except ValueError:
            logging.warning(f"Environment variable {name} could not be cast to {cast_type.__name__}")
    return value

class Config:
    """Base configuration class with default settings."""
    
    APP_NAME = get_env_variable("APP_NAME")
    SECRET_KEY = get_env_variable("SECRET_KEY", "SECRET_KEY_ENV_VAR_NOT_SET")
    
    if SECRET_KEY == "SECRET_KEY_ENV_VAR_NOT_SET":
        logging.warning("SECRET KEY ENV VAR NOT SET! SHOULD NOT SEE IN PRODUCTION")
    
    # Email configuration
    MAIL_SERVER = get_env_variable("MAIL_SERVER")
    MAIL_PORT = get_env_variable("MAIL_PORT", 587, int)
    MAIL_USE_TLS = get_env_variable("MAIL_USE_TLS", True, bool)
    MAIL_USE_SSL = get_env_variable("MAIL_USE_SSL", False, bool)
    MAIL_USERNAME = get_env_variable("MAIL_USERNAME")
    MAIL_PASSWORD = get_env_variable("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = get_env_variable("MAIL_DEFAULT_SENDER")
    
    # Application settings
    SERIALIZER_SALT = get_env_variable("SERIALIZER_SALT")
    RICH_LOGGING = get_env_variable("RICH_LOGGING", True, bool)

    
    # Admin account settings
    ADMIN_PASSWORD = get_env_variable("ADMIN_PASSWORD", "Password")
    ADMIN_EMAIL = get_env_variable("ADMIN_EMAIL", "admin@test.com")
    EMAIL_SUBJECT_PREFIX = f"[{APP_NAME}]"
    
    # AWS configuration
    # Redis configuration
    REDIS_URL = get_env_variable("REDIS_URL")
    if REDIS_URL:
        urlparse.uses_netloc.append("redis")
        url = urlparse.urlparse(REDIS_URL)
        
        RQ_DEFAULT_HOST = url.hostname
        RQ_DEFAULT_PORT = url.port
        RQ_DEFAULT_PASSWORD = url.password
        RQ_DEFAULT_DB = 0
        RQ_DEFAULT_URL = REDIS_URL
        
    # Search parameters
    MSEARCH_INDEX_NAME = "msearch"
    MSEARCH_BACKEND = "simple"
    MSEARCH_PRIMARY_KEY = "id"
    MSEARCH_ENABLE = True
    MSEARCH_LOGGER = logging.DEBUG
    
    # SQLAlchemy settings
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    
    
    # CORS allowed domains
    ALLOWED_ORIGINS = [
        r".*\.gitpod\.io$",
        "http://localhost:5000",
    ]
    
    # Upload paths
    UPLOADED_IMAGES_DEST = "/tmp/uploads"
    
    
    @staticmethod
    def init_app(app):
        """Initialization method for setting up the app."""
        pass

class DevelopmentConfig(Config):
    """Development-specific configuration."""
    
    DEBUG = True
    ASSETS_DEBUG = True
    TESTING = False
    TEMPLATES_AUTO_RELOAD = True
    SQLALCHEMY_DATABASE_URI = get_env_variable("DEV_DATABASE_URL")
    
    @classmethod
    def init_app(cls, app):
        logging.info("THIS APP IS IN DEBUG MODE. YOU SHOULD NOT SEE THIS IN PRODUCTION.")

class TestingConfig(Config):
    """Testing-specific configuration."""
    
    TESTING = True
    SQLALCHEMY_DATABASE_URI = get_env_variable("TEST_DATABASE_URL")
    WTF_CSRF_ENABLED = False
    
    @classmethod
    def init_app(cls, app):
        logging.info("THIS APP IS IN TESTING MODE. YOU SHOULD NOT SEE THIS IN PRODUCTION.")

class ProductionConfig(Config):
    """Production-specific configuration."""
    
    DEBUG = False
    USE_RELOADER = False
    SQLALCHEMY_DATABASE_URI = get_env_variable("DATABASE_URL")
    SSL_DISABLE = get_env_variable("SSL_DISABLE", "True") == "True"
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        assert cls.SECRET_KEY != "SECRET_KEY_ENV_VAR_NOT_SET", "SECRET_KEY IS NOT SET!"

class HerokuConfig(ProductionConfig):
    """Heroku-specific configuration."""
    
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)
        
        # Handle proxy server headers
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

class StagingConfig(ProductionConfig):
    """Staging-specific configuration."""
    
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)
        
        # Log to syslog
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)

# Configuration mapping
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
    "heroku": HerokuConfig,
    "staging": StagingConfig,
}
