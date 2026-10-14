from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from moxart import db
from moxart.models.category import Category
from moxart.models.post import Post, PostSchema
from moxart.services import sanitize_html, unique_post_slug
from moxart.utils.decorator import confirmed_required
from moxart.utils.request import json_body, required_fields
from moxart.utils.security import ValidationError

bp = Blueprint('post', __name__, url_prefix='/api')

DEFAULT_CATEGORY_SLUG = 'uncategorized'
TITLE_MAX_LENGTH = 255
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100
EDITABLE_FIELDS = ('title', 'content', 'category_public_id')


@bp.route('/post', methods=['POST'])
@confirmed_required
def new_post():
    data = json_body()
    title, content = required_fields(data, 'title', 'content')

    _validate_post_fields(title, content)

    category = _resolve_category(data.get('category_public_id'))

    if category is None:
        return jsonify(status=400, msg='category not found'), 400

    # the author is always the logged-in user, never a value from the request body
    post = Post(user_public_id=current_user.user_public_id, category_public_id=category.category_public_id,
                title=title, title_slug=unique_post_slug(title), content=sanitize_html(content))

    db.session.add(post)
    db.session.commit()

    return jsonify(status=201, msg='post has been successfully published', post_public_id=post.post_public_id), 201


@bp.route('/post/<uuid:post_public_id>')
def get_post(post_public_id):
    post = _get_post(str(post_public_id))

    if post is None:
        return jsonify(status=404, msg='post not found'), 404

    return jsonify(status=200, data=PostSchema().dump(post)), 200


@bp.route('/post/slug/<slug>')
def get_post_by_slug(slug):
    post = db.session.execute(db.select(Post).filter_by(title_slug=slug)).scalar_one_or_none()

    if post is None:
        return jsonify(status=404, msg='post not found'), 404

    return jsonify(status=200, data=PostSchema().dump(post)), 200


@bp.route('/posts', methods=['GET'])
def get_all_posts():
    page = _positive_int_arg('page', 1)
    per_page = min(_positive_int_arg('per_page', DEFAULT_PER_PAGE), MAX_PER_PAGE)

    # the id tie-breaker keeps the order stable when posts share a timestamp
    query = db.select(Post).order_by(Post.published_at.desc(), Post.id)
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    return jsonify(status=200, data=PostSchema(many=True).dump(pagination.items), pagination={
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages,
    }), 200


@bp.route('/post/<post_public_id>', methods=['PUT'])
@confirmed_required
def edit_post(post_public_id):
    data = json_body()
    post = _get_post(post_public_id)

    if post is None:
        return jsonify(status=404, msg='post not found'), 404

    if not current_user.admin and post.user_public_id != current_user.user_public_id:
        return jsonify(status=403, msg="you don't have permission to edit this post"), 403

    if not any(data.get(name) is not None for name in EDITABLE_FIELDS):
        return jsonify(status=400, msg='nothing to update, send at least one of: {}'.format(
            ', '.join(EDITABLE_FIELDS))), 400

    title, content = data.get('title', post.title), data.get('content', post.content)
    _validate_post_fields(title, content)

    if data.get('category_public_id') is not None:
        category = _resolve_category(data['category_public_id'])

        if category is None:
            return jsonify(status=400, msg='category not found'), 400

        post.category_public_id = category.category_public_id

    # the slug stays the same when the title changes so existing links keep working
    post.title = title
    post.content = sanitize_html(content)
    db.session.commit()

    return jsonify(status=200, msg='post has been successfully updated', data=PostSchema().dump(post)), 200


@bp.route('/post/<post_public_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_public_id):
    post = _get_post(post_public_id)

    if post is None:
        return jsonify(status=404, msg='post not found'), 404

    if not current_user.admin and post.user_public_id != current_user.user_public_id:
        return jsonify(status=403, msg="you don't have permission to delete this post"), 403

    db.session.delete(post)
    db.session.commit()

    return jsonify(status=200, msg='post has been successfully deleted'), 200


def _get_post(post_public_id):
    return db.session.execute(db.select(Post).filter_by(post_public_id=post_public_id)).scalar_one_or_none()


def _validate_post_fields(title, content):
    if not isinstance(title, str) or len(title) > TITLE_MAX_LENGTH or not isinstance(content, str):
        raise ValidationError('title and content must be text, title at most 255 characters')


def _resolve_category(category_public_id):
    if category_public_id:
        query = db.select(Category).filter_by(category_public_id=str(category_public_id))
    else:
        query = db.select(Category).filter_by(category_name_slug=DEFAULT_CATEGORY_SLUG)

    return db.session.execute(query).scalar_one_or_none()


def _positive_int_arg(name, default):
    value = request.args.get(name, default)

    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 0

    if number < 1:
        raise ValidationError('{} must be a positive integer'.format(name))

    return number
