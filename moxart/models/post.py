import uuid

from marshmallow import Schema, fields
from moxart import db
from moxart.utils.time import utcnow


class Post(db.Model):
    __tablename__ = 'post'

    id = db.Column(db.String(50), primary_key=True, unique=True, nullable=False)
    post_public_id = db.Column(db.String(50), unique=True, nullable=False)
    user_public_id = db.Column(db.String(50), db.ForeignKey('user.user_public_id'))
    category_public_id = db.Column(db.String(50), db.ForeignKey('category.category_public_id'))
    score = db.Column(db.Integer, nullable=False, default=0)
    title = db.Column(db.Text)
    title_slug = db.Column(db.String(100), unique=True, nullable=False)
    content = db.Column(db.Text)
    comment_count = db.Column(db.Integer, default=0)
    published_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def __init__(self, user_public_id, category_public_id, title, title_slug, content):
        self.id = str(uuid.uuid4())
        self.user_public_id = user_public_id
        self.post_public_id = str(uuid.uuid4())
        self.category_public_id = category_public_id
        self.title = title
        self.title_slug = title_slug
        self.content = content

    def __repr__(self):
        return '<Post {}>'.format(self.post_public_id)


class PostSchema(Schema):
    post_public_id = fields.Str()
    user_public_id = fields.Str()
    category_public_id = fields.Str()
    title = fields.Str()
    title_slug = fields.Str()
    content = fields.Str()
    comment_count = fields.Int()
    published_at = fields.DateTime()
    updated_at = fields.DateTime()
