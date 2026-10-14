import nh3
from slugify import slugify
from sqlalchemy.exc import IntegrityError

from moxart import db
from moxart.models.post import Post
from moxart.models.profile import Profile
from moxart.models.user import User
from moxart.utils.security import (
    ValidationError, hash_password, verify_password, validate_username, validate_email, validate_password
)

PROFILE_FIELDS = ('first_name', 'last_name', 'nickname', 'url', 'bio', 'location', 'display_name')
PROFILE_MAX_LENGTH = {'first_name': 50, 'last_name': 50, 'nickname': 50, 'url': 100, 'location': 50,
                      'display_name': 50, 'bio': 5000}
SLUG_MAX_LENGTH = 100


class Forbidden(Exception):
    pass


class Conflict(Exception):
    pass


def can_manage(actor, user):
    return actor.admin or actor.user_public_id == user.user_public_id


def get_user(public_id):
    return db.session.execute(db.select(User).filter_by(user_public_id=public_id)).scalar_one_or_none()


def update_user(actor, user, data):
    """Apply a partial update; returns True when the caller's tokens were invalidated."""
    if not can_manage(actor, user):
        raise Forbidden()

    password_changed = False

    if data.get('username') is not None:
        user.username = validate_username(data['username'])

    if data.get('email') is not None:
        email = validate_email(data['email'])

        if email != user.email:
            user.email = email
            user.confirmed = False
            user.confirmed_at = None

    if data.get('password') is not None:
        # a stolen access token alone must not be enough to take over the account
        if not actor.admin and not verify_password(user.password, str(data.get('current_password', ''))):
            raise ValidationError('current_password is not correct')

        user.password = hash_password(validate_password(data['password']))
        password_changed = True

    _update_profile(user, data)

    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise Conflict() from error

    return password_changed and actor.user_public_id == user.user_public_id


def delete_user(actor, user):
    if not can_manage(actor, user):
        raise Forbidden()

    if user.admin:
        raise ValidationError('admin users can only be removed from the command line')

    db.session.delete(user)
    db.session.commit()


def _update_profile(user, data):
    changes = {name: data[name] for name in PROFILE_FIELDS if data.get(name) is not None}

    if not changes:
        return

    for name, value in changes.items():
        if not isinstance(value, str) or len(value) > PROFILE_MAX_LENGTH[name]:
            raise ValidationError('{} must be text of at most {} characters'.format(name, PROFILE_MAX_LENGTH[name]))

    if user.profile is None:
        user.profile = Profile(**{name: None for name in PROFILE_FIELDS})
        user.profile.user_public_id = user.user_public_id

    for name, value in changes.items():
        setattr(user.profile, name, value)


def sanitize_html(content):
    # post content is rendered as HTML by the front end, so strip scripts, handlers and unsafe urls
    return nh3.clean(content)


def unique_post_slug(title):
    base = slugify(title, max_length=SLUG_MAX_LENGTH - 9) or 'post'
    slug = base
    suffix = 2

    while db.session.execute(db.select(Post.id).filter_by(title_slug=slug)).first() is not None:
        slug = '{}-{}'.format(base, suffix)
        suffix += 1

    return slug
