import os
from datetime import timedelta

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
mail = Mail()
limiter = Limiter(key_func=get_remote_address)

REQUIRED_SECRETS = ('SECRET_KEY', 'JWT_SECRET_KEY', 'SECURITY_PASSWORD_SALT')
MIN_SIGNING_KEY_LENGTH = 32
PLACEHOLDER_SECRETS = {'', 'secret-key-here', 'jwt-secret-key-here', 'change-me'}


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI='mysql+pymysql://moxart:password@localhost/moxart',
        SQLALCHEMY_ENGINE_OPTIONS={'pool_pre_ping': True},

        JWT_TOKEN_LOCATION=['headers', 'cookies'],
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=1),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),
        JWT_COOKIE_CSRF_PROTECT=True,
        JWT_COOKIE_SECURE=False,
        JWT_COOKIE_SAMESITE='Lax',

        # base url used to build links inside emails
        SERVER_BASE_URL='http://localhost:5000',

        CONFIRM_TOKEN_MAX_AGE=60 * 60 * 24,
        RESET_TOKEN_MAX_AGE=60 * 30,

        UPLOAD_BASE_PATH=os.path.join(app.instance_path, 'uploads'),
        UPLOAD_VALID_FILE=['.jpg', '.jpeg', '.png', '.gif', '.zip', '.tar.gz', '.rar'],
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,

        RATELIMIT_STORAGE_URI='memory://',
        RATELIMIT_HEADERS_ENABLED=True,
    )

    if config is None:
        app.config.from_pyfile('config.py', silent=True)
        # environment variables such as MOXART_SECRET_KEY override the config file
        app.config.from_prefixed_env('MOXART')
    else:
        app.config.from_mapping(config)

    _check_secrets(app)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_BASE_PATH'], exist_ok=True)

    # initialize plugins
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    limiter.init_app(app)

    with app.app_context():
        # include our models
        from .models import user, role, post, profile, category, comment, token  # noqa: F401

        from . import errors, jwt_callbacks  # noqa: F401
        from .routes.dashboard import dashboard_user
        from .routes import auth, confirm, upload
        from .routes.api import user as user_api, post as post_api, category as category_api

        errors.register(app)

        # register blueprints
        app.register_blueprint(dashboard_user.bp)
        app.register_blueprint(auth.bp)
        app.register_blueprint(confirm.bp)
        app.register_blueprint(upload.bp)
        app.register_blueprint(user_api.bp)
        app.register_blueprint(post_api.bp)
        app.register_blueprint(category_api.bp)

    app.after_request(_set_security_headers)

    return app


def _check_secrets(app):
    if app.testing:
        return

    missing = [key for key in REQUIRED_SECRETS if app.config.get(key) in (None, *PLACEHOLDER_SECRETS)]

    if missing:
        raise RuntimeError(
            'missing secret configuration: {}. Set them in instance/config.py '
            'or as MOXART_<NAME> environment variables'.format(', '.join(missing)))

    for key in ('SECRET_KEY', 'JWT_SECRET_KEY'):
        if len(app.config[key]) < MIN_SIGNING_KEY_LENGTH:
            app.logger.warning('%s is shorter than %d characters and can be brute-forced; generate one with '
                               '`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`',
                               key, MIN_SIGNING_KEY_LENGTH)


def _set_security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Referrer-Policy', 'same-origin')
    response.headers.setdefault('Content-Security-Policy', "default-src 'none'; frame-ancestors 'none'")

    return response
