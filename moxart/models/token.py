from moxart import db
from moxart.utils.time import utcnow


class TokenBlocklist(db.Model):
    """JWT ids revoked by logout; checked on every authenticated request."""
    __tablename__ = 'token_blocklist'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, index=True, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
