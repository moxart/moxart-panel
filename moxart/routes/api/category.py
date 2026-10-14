from flask import Blueprint, jsonify
from slugify import slugify
from sqlalchemy.exc import IntegrityError

from moxart import db
from moxart.models.category import Category, CategorySchema
from moxart.utils.decorator import admin_required
from moxart.utils.request import json_body, required_fields

bp = Blueprint('category', __name__, url_prefix='/api')

NAME_MAX_LENGTH = 100


@bp.route('/category', methods=['POST'])
@admin_required
def new_category():
    category_name, = required_fields(json_body(), 'category_name')

    if not isinstance(category_name, str) or len(category_name) > NAME_MAX_LENGTH or not slugify(category_name):
        return jsonify(status=400, msg='category_name must be text of at most 100 characters'), 400

    category = Category(category_name=category_name.strip())

    try:
        db.session.add(category)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(status=409, msg='category already exists'), 409

    return jsonify(status=201, msg='category has been successfully created',
                   category_public_id=category.category_public_id), 201


@bp.route('/category/<uuid:category_public_id>')
def get_category(category_public_id):
    category = db.session.execute(
        db.select(Category).filter_by(category_public_id=str(category_public_id))).scalar_one_or_none()

    if category is None:
        return jsonify(status=404, msg='category not found'), 404

    return jsonify(status=200, data=CategorySchema().dump(category)), 200


@bp.route('/categories', methods=['GET'])
def get_categories():
    categories = db.session.execute(db.select(Category).order_by(Category.category_name)).scalars().all()

    return jsonify(status=200, data=CategorySchema(many=True).dump(categories)), 200
