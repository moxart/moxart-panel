import os

from flask import current_app, Blueprint, jsonify
from flask_jwt_extended import current_user

from moxart import db
from moxart.models.user import User, UserSchema, PublicUserSchema
from moxart.services import Forbidden, Conflict, can_manage, get_user, update_user, delete_user
from moxart.utils.decorator import admin_required, confirmed_required
from moxart.utils.email import send_confirmation_email
from moxart.utils.request import json_body
from moxart.utils.security import ValidationError
from moxart.utils.upload import user_upload_dir

bp = Blueprint('user', __name__, url_prefix='/api')


@bp.route('/users', methods=['GET', 'POST'])
@admin_required
def get_users():
    users = db.session.execute(db.select(User).order_by(User.registered_at)).scalars().all()

    return jsonify(UserSchema(many=True).dump(users)), 200


@bp.route('/user/<public_id>', methods=['GET'])
@confirmed_required
def get_user_detail(public_id):
    user = get_user(public_id)

    if user is None:
        return jsonify(status=404, msg='user not found'), 404

    # other users only see the public fields, never the email address
    schema = UserSchema() if can_manage(current_user, user) else PublicUserSchema()

    return jsonify(status=200, logged_in_as=current_user.username, data=schema.dump(user)), 200


@bp.route('/user/<public_id>', methods=['PUT'])
@confirmed_required
def edit_user(public_id):
    data = json_body()
    user = get_user(public_id)

    if user is None:
        return jsonify(status=404, msg='user not found'), 404

    previous_email, previous_username = user.email, user.username

    try:
        relogin_required = update_user(current_user, user, data)
    except Forbidden:
        return jsonify(status=403, msg="you don't have permission to edit this user"), 403
    except Conflict:
        return jsonify(status=409, msg='username or email address already exists please choose another'), 409

    if user.email != previous_email:
        send_confirmation_email(user)

    if user.username != previous_username:
        _move_upload_dir(previous_username, user.username)

    return jsonify(status=200, msg='user has been successfully updated', relogin_required=relogin_required), 200


@bp.route('/user/<public_id>', methods=['DELETE'])
@confirmed_required
def remove_user(public_id):
    user = get_user(public_id)

    if user is None:
        return jsonify(status=404, msg='user not found'), 404

    try:
        delete_user(current_user, user)
    except Forbidden:
        return jsonify(status=403, msg="you don't have permission to delete this user"), 403

    return jsonify(status=200, msg='user has been successfully deleted'), 200


def _move_upload_dir(old_username, new_username):
    base = current_app.config['UPLOAD_BASE_PATH']
    new_dir = user_upload_dir(base, new_username)

    try:
        old_dir = user_upload_dir(base, old_username)
    except ValidationError:
        # accounts created before usernames were validated may not have a usable directory
        old_dir = None

    if old_dir and os.path.isdir(old_dir) and not os.path.exists(new_dir):
        os.rename(old_dir, new_dir)
    else:
        os.makedirs(new_dir, exist_ok=True)
