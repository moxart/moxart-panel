from moxart import db


class Role(db.Model):
    __tablename__ = 'role'

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer)
    user_public_id = db.Column(db.String(50), db.ForeignKey('user.user_public_id'))
