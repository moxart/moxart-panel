import re

import pytest

from moxart import create_app, db, mail
from moxart.models.category import Category
from moxart.models.user import User
from moxart.utils.security import hash_password

PASSWORD = 'correct-horse-battery'


@pytest.fixture
def app(tmp_path):
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key-that-is-long-enough-1234',
        'JWT_SECRET_KEY': 'test-jwt-secret-key-that-is-long-enough-1234',
        'SECURITY_PASSWORD_SALT': 'test-salt',
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'RATELIMIT_ENABLED': False,
        'MAIL_SUPPRESS_SEND': True,
        'MAIL_DEFAULT_SENDER': 'noreply@example.com',
        'UPLOAD_BASE_PATH': str(tmp_path / 'uploads'),
    })

    with app.app_context():
        db.create_all()
        db.session.add(Category(category_name='Uncategorized'))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def outbox(app):
    with mail.record_messages() as messages:
        yield messages


def make_user(username, admin=False, confirmed=True, password=PASSWORD):
    user = User(username=username, email='{}@example.com'.format(username), password=hash_password(password),
                admin=admin, confirmed=confirmed)
    db.session.add(user)
    db.session.commit()

    return user


def login(client, username, password=PASSWORD):
    resp = client.post('/login', json={'username': username, 'password': password})
    assert resp.status_code == 200, resp.get_json()

    return resp.get_json()['access_token']


def auth(token):
    return {'Authorization': 'Bearer {}'.format(token)}


def link_token(message):
    return re.search(r'/(?:confirm|reset/password)/([^"\s<]+)', message.html).group(1)


def reset_token(message):
    return re.search(r'<pre>([^<]+)</pre>', message.html).group(1)
