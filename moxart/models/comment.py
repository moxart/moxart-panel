import uuid

from marshmallow import Schema, fields
from moxart import db
from moxart.utils.time import utcnow


class Comment(db.Model):
    __tablename__ = 'comment'

    id = db.Column(db.String(50), primary_key=True, unique=True, nullable=False)
    post_public_id = db.Column(db.String(50), nullable=False)
    user_public_id = db.Column(db.String(50), db.ForeignKey('user.user_public_id'))
    score = db.Column(db.Integer, nullable=False, default=0)
    text = db.Column(db.Text)
    published_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    # FOREIGN KEYS #
    # `user_public_id` #
    # END FOREIGN KEYS #

    def __init__(self, user_public_id, post_public_id, score, text):
        self.id = str(uuid.uuid4())
        self.user_public_id = user_public_id
        self.post_public_id = post_public_id
        self.score = score
        self.text = text

    def __repr__(self):
        return '<ID {}>'.format(self.id)


class CommentSchema(Schema):
    post_public_id = fields.Str()
    user_public_id = fields.Str()
    score = fields.Int()
    text = fields.Str()
    published_at = fields.DateTime()
