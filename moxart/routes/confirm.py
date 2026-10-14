from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, current_user

from moxart import db, limiter
from moxart.models.user import User
from moxart.utils.email import send_confirmation_email, send_reset_email
from moxart.utils.request import json_body, required_fields
from moxart.utils.security import hash_password, validate_password
from moxart.utils.time import utcnow
from moxart.utils.token import InvalidToken, confirm_token, load_reset_token, password_fingerprint

bp = Blueprint('confirm', __name__)


@bp.route('/confirm/<token>', methods=['GET'])
def confirm_email(token):
    try:
        email = confirm_token(token)
    except InvalidToken:
        return jsonify(status=400, msg='the confirmation link is invalid or has expired'), 400

    user = _user_by_email(email)

    if user is None:
        return jsonify(status=400, msg='the confirmation link is invalid or has expired'), 400

    if user.confirmed:
        return jsonify(status=200, msg='account already confirmed. Please login'), 200

    user.confirmed = True
    user.confirmed_at = utcnow()
    db.session.commit()

    return jsonify(status=200, msg='you have confirmed your account'), 200


@bp.route('/unconfirmed')
@jwt_required()
def unconfirmed():
    if current_user.confirmed:
        return jsonify(status=200, msg='you are logged in'), 200

    return jsonify(status=401, msg='please confirm your account'), 401


@bp.route('/resend/confirm', methods=['POST'])
@limiter.limit('3 per hour')
@jwt_required()
def resend_confirmation():
    if current_user.confirmed:
        return jsonify(status=200, msg='account already confirmed. Please login'), 200

    if not send_confirmation_email(current_user):
        return jsonify(status=503, msg='confirmation email could not be sent, try again later'), 503

    return jsonify(status=200, msg='a new confirmation email has been sent'), 200


@bp.route('/send/token', methods=['POST'])
@limiter.limit('5 per hour')
def send_reset_token():
    email, = required_fields(json_body(), 'email')

    user = _user_by_email(str(email).strip().lower())

    if user is not None:
        send_reset_email(user)

    # same answer either way so this endpoint can't be used to discover registered emails
    return jsonify(status=200, msg='If your email is valid, an email will be sent to you'), 200


@bp.route('/reset/password/<token>', methods=['POST'])
@limiter.limit('10 per hour')
def reset_password(token):
    password, = required_fields(json_body(), 'password')
    password = validate_password(password)

    try:
        data = load_reset_token(token)
    except InvalidToken:
        return jsonify(status=400, msg='the reset link is invalid or has expired'), 400

    user = _user_by_email(data['email'])

    if user is None or data['pwd'] != password_fingerprint(user.password):
        return jsonify(status=400, msg='the reset link is invalid or has expired'), 400

    user.password = hash_password(password)
    db.session.commit()

    return jsonify(status=200, msg='your password has been reset successfully'), 200


def _user_by_email(email):
    return db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
