import hashlib
import hmac

from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

CONFIRM_PURPOSE = 'email-confirm'
RESET_PURPOSE = 'password-reset'


class InvalidToken(Exception):
    pass


def _serializer(purpose):
    # a distinct salt per purpose stops a confirmation link from being replayed as a reset link
    salt = '{}:{}'.format(current_app.config['SECURITY_PASSWORD_SALT'], purpose)

    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=salt)


def password_fingerprint(password_hash):
    """Short HMAC of the stored hash; changes whenever the password does."""
    key = current_app.config['SECRET_KEY'].encode()

    return hmac.new(key, password_hash.encode(), hashlib.sha256).hexdigest()[:16]


def generate_confirmation_token(email):
    return _serializer(CONFIRM_PURPOSE).dumps(email)


def confirm_token(token):
    return _load(CONFIRM_PURPOSE, token, current_app.config['CONFIRM_TOKEN_MAX_AGE'])


def generate_reset_token(user):
    # binding the token to the current password hash makes it single-use
    return _serializer(RESET_PURPOSE).dumps({'email': user.email, 'pwd': password_fingerprint(user.password)})


def load_reset_token(token):
    data = _load(RESET_PURPOSE, token, current_app.config['RESET_TOKEN_MAX_AGE'])

    if not isinstance(data, dict) or 'email' not in data or 'pwd' not in data:
        raise InvalidToken()

    return data


def _load(purpose, token, max_age):
    try:
        return _serializer(purpose).loads(token, max_age=max_age)
    except (SignatureExpired, BadSignature) as error:
        raise InvalidToken() from error
