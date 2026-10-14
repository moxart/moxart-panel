from flask import jsonify

from moxart import db, jwt
from moxart.models.token import TokenBlocklist
from moxart.models.user import User
from moxart.utils.token import password_fingerprint


# tokens carry the immutable public id, so renaming a user keeps their session valid
@jwt.user_identity_loader
def user_identity(user):
    return user.user_public_id


@jwt.additional_claims_loader
def add_claims_to_token(user):
    return {'roles': 'admin' if user.admin else 'guest', 'pwd': password_fingerprint(user.password)}


@jwt.user_lookup_loader
def load_user(_header, payload):
    user = db.session.execute(db.select(User).filter_by(user_public_id=payload['sub'])).scalar_one_or_none()

    # a password change invalidates every token issued before it
    if user is None or payload.get('pwd') != password_fingerprint(user.password):
        return None

    return user


@jwt.token_in_blocklist_loader
def check_if_token_revoked(_header, payload):
    return db.session.execute(db.select(TokenBlocklist.id).filter_by(jti=payload['jti'])).first() is not None


@jwt.user_lookup_error_loader
def user_lookup_error(_header, _payload):
    return jsonify(status=401, msg='token is no longer valid, please login again'), 401


@jwt.revoked_token_loader
def revoked_token(_header, _payload):
    return jsonify(status=401, msg='token has been revoked'), 401


@jwt.expired_token_loader
def expired_token(_header, _payload):
    return jsonify(status=401, msg='token has expired'), 401


@jwt.invalid_token_loader
def invalid_token(reason):
    return jsonify(status=401, msg=reason), 401


@jwt.unauthorized_loader
def missing_token(reason):
    return jsonify(status=401, msg=reason), 401
