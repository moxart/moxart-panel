import uuid

from marshmallow import Schema, fields
from moxart import db



class Profile(db.Model):
    __tablename__ = 'profile'

    id = db.Column(db.String(50), primary_key=True, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_public_id = db.Column(db.String(50), db.ForeignKey('user.user_public_id'))
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    nickname = db.Column(db.String(50), nullable=True)
    url = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text)
    location = db.Column(db.String(50))
    display_name = db.Column(db.String(50), nullable=True)
    status = db.Column(db.Boolean)

    def __init__(self,
                 first_name, last_name, nickname, url, bio, location,
                 display_name, status=True):
        self.first_name = first_name
        self.last_name = last_name
        self.nickname = nickname
        self.url = url
        self.bio = bio
        self.location = location
        self.display_name = display_name
        self.status = status

    def __repr__(self):
        return '<Profile {}>'.format(self.id)


class ProfileSchema(Schema):
    first_name = fields.Str()
    last_name = fields.Str()
    nickname = fields.Str()
    url = fields.Str()
    bio = fields.Str()
    location = fields.Str()
    display_name = fields.Str()
    status = fields.Boolean()
