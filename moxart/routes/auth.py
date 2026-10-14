from datetime import datetime, timezone

from flask import current_app, Blueprint, jsonify
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import (
    jwt_required, current_user, get_jwt,
    create_access_token, create_refresh_token,
    set_access_cookies, set_refresh_cookies, unset_jwt_cookies
)
from moxart import db, limiter
from moxart.models.role import Role
from moxart.models.token import TokenBlocklist
from moxart.models.user import User
from moxart.utils.email import send_confirmation_email
from moxart.utils.request import json_body, required_fields
from moxart.utils.security import (
    hash_password, verify_password, validate_username, validate_email, validate_password
)
from moxart.utils.time import utcnow
from moxart.utils.upload import init_client_upload_dir

bp = Blueprint('auth', __name__)

GUEST_ROLE_ID = 2


@bp.route('/register', methods=['POST'])
@limiter.limit('10 per hour')
def signup_user():
    username, email, password = required_fields(json_body(), 'username', 'email', 'password')

    username = validate_username(username)
    email = validate_email(email)
    password = validate_password(password)

    user = User(username=username, email=email, password=hash_password(password), admin=False, confirmed=False)

    try:
        db.session.add(user)
        db.session.flush()
        db.session.add(Role(role_id=GUEST_ROLE_ID, user_public_id=user.user_public_id))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()

        return jsonify(status=409, register=False,
                       msg='username or email address already exists please choose another'), 409

    init_client_upload_dir(current_app.config['UPLOAD_BASE_PATH'], user.username)
    send_confirmation_email(user)

    resp = _token_response(user, status=201, register=True, msg='user has been registered successfully',
                           current_email=email)

    return resp, 201


@bp.route('/login', methods=['POST'])
@limiter.limit('10 per minute')
def login_user():
    username, password = required_fields(json_body(), 'username', 'password')

    user = db.session.execute(db.select(User).filter_by(username=str(username))).scalar_one_or_none()

    # always run a hash check so response time doesn't reveal whether the username exists
    password_ok = verify_password(user.password if user else None, str(password))

    if not user or not password_ok:
        return jsonify(status=401, login=False, msg='user authentication invalid'), 401

    user.last_activity = utcnow()
    db.session.commit()

    return _token_response(user, status=200, login=True, msg='user has been authenticated successfully'), 200


@bp.route('/token/refresh', methods=['POST'])
@jwt_required(refresh=True)
def token_refresh():
    access_token = create_access_token(identity=current_user)

    resp = jsonify(status=200, refresh=True, access_token=access_token,
                   msg='the access token has been successfully refreshed')
    set_access_cookies(resp, access_token)

    return resp, 200


@bp.route('/logout', methods=['DELETE'])
@jwt_required(verify_type=False)
def logout_user():
    token = get_jwt()
    now = utcnow()

    db.session.execute(db.delete(TokenBlocklist).where(TokenBlocklist.expires_at < now))
    db.session.add(TokenBlocklist(
        jti=token['jti'],
        expires_at=datetime.fromtimestamp(token['exp'], timezone.utc).replace(tzinfo=None)))
    db.session.commit()

    resp = jsonify(status=200, logout=True, msg='user has been successfully logged out')
    unset_jwt_cookies(resp)

    return resp, 200


def _token_response(user, **body):
    access_token = create_access_token(identity=user)
    refresh_token = create_refresh_token(identity=user)

    resp = jsonify(**body, access_token=access_token, refresh_token=refresh_token)
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)

    return resp
