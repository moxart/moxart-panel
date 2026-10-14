import re

from werkzeug.security import generate_password_hash, check_password_hash

USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_.-]{3,50}$')
EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MIN_PASSWORD_LENGTH = 8

# hash checked against unknown usernames so login timing doesn't reveal which accounts exist
DUMMY_PASSWORD_HASH = generate_password_hash('dummy-password')


class ValidationError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password_hash, password):
    return check_password_hash(password_hash or DUMMY_PASSWORD_HASH, password)


def validate_username(username):
    # usernames name the per-user upload directory, so they must never contain path separators
    if not isinstance(username, str) or not USERNAME_PATTERN.match(username) or username in ('.', '..'):
        raise ValidationError('username must be 3-50 characters: letters, digits, "_", "-" or "."')

    return username


def validate_email(email):
    if not isinstance(email, str) or len(email) > 255 or not EMAIL_PATTERN.match(email):
        raise ValidationError('email address is not valid')

    return email.strip().lower()


def validate_password(password):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError('password must be at least {} characters'.format(MIN_PASSWORD_LENGTH))

    return password
