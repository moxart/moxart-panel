from flask import Blueprint, jsonify
from flask_jwt_extended import current_user

from moxart import db
from moxart.models.user import User, UserSchema
from moxart.services import delete_user
from moxart.utils.decorator import admin_required

bp = Blueprint('dashboard_user', __name__, url_prefix='/dashboard')


@bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    users = db.session.execute(db.select(User).order_by(User.registered_at)).scalars().all()

    return jsonify(data=UserSchema(many=True).dump(users)), 200


@bp.route('/user/<username>', methods=['DELETE'])
@admin_required
def remove_user(username):
    user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()

    if user is None:
        return jsonify(status=404, msg='user not found'), 404

    delete_user(current_user, user)

    return jsonify(status=200, msg='user has been successfully deleted'), 200
