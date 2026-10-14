import uuid

from marshmallow import Schema, fields
from moxart import db
from moxart.utils.time import utcnow
from slugify import slugify


class Category(db.Model):
    __tablename__ = 'category'

    id = db.Column(db.String(50), primary_key=True, unique=True, nullable=False)
    category_public_id = db.Column(db.String(50), unique=True, nullable=False)
    category_name = db.Column(db.String(100), unique=True, nullable=False)
    category_name_slug = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

    post = db.relationship('Post', backref='category', lazy=True)

    def __init__(self, category_name):
        self.id = str(uuid.uuid4())
        self.category_public_id = str(uuid.uuid4())
        self.category_name = category_name
        self.category_name_slug = slugify(category_name)
        self.created_at = utcnow()

    def __repr__(self):
        return '<Category {} {}>'.format(self.category_name, self.category_public_id)


class CategorySchema(Schema):
    category_public_id = fields.Str()
    category_name = fields.Str()
    category_name_slug = fields.Str()
    created_at = fields.DateTime()
