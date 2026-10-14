from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, current_user


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()

        # checked against the database, so revoking admin takes effect immediately
        if not current_user.admin:
            return jsonify(status=403, msg="you don't have permission to access this endpoint"), 403

        return fn(*args, **kwargs)

    return wrapper


def confirmed_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()

        if not current_user.confirmed:
            return jsonify(status=401, msg='please confirm your account'), 401

        return fn(*args, **kwargs)

    return wrapper
