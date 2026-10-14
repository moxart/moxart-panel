import pytest

from moxart import create_app
from tests.conftest import PASSWORD, auth, link_token, login, make_user, reset_token


def test_register_creates_unconfirmed_user_and_sends_confirmation(client, outbox):
    resp = client.post('/register', json={'username': 'alice', 'email': 'Alice@Example.com', 'password': PASSWORD})

    assert resp.status_code == 201
    assert resp.get_json()['current_email'] == 'alice@example.com'
    assert len(outbox) == 1

    resp = client.get('/confirm/' + link_token(outbox[0]))
    assert resp.status_code == 200
    assert client.get('/unconfirmed', headers=auth(login(client, 'alice'))).status_code == 200


@pytest.mark.parametrize('username', ['../evil', 'a/b', '..', 'x', ''])
def test_register_rejects_unsafe_usernames(client, username):
    resp = client.post('/register', json={'username': username, 'email': 'e@example.com', 'password': PASSWORD})

    assert resp.status_code == 400


def test_register_rejects_short_password_and_non_json(client):
    assert client.post('/register', json={'username': 'bob', 'email': 'b@example.com',
                                          'password': 'short'}).status_code == 400
    assert client.post('/register', data='nope').status_code == 400


def test_register_duplicate_is_conflict(client):
    body = {'username': 'alice', 'email': 'alice@example.com', 'password': PASSWORD}
    client.post('/register', json=body)

    assert client.post('/register', json=body).status_code == 409


def test_login_rejects_bad_credentials(client, app):
    make_user('alice')

    assert client.post('/login', json={'username': 'alice', 'password': 'wrong-password'}).status_code == 401
    assert client.post('/login', json={'username': 'nobody', 'password': PASSWORD}).status_code == 401


def test_logout_revokes_token(client, app):
    make_user('alice')
    token = login(client, 'alice')

    assert client.delete('/logout', headers=auth(token)).status_code == 200
    assert client.get('/unconfirmed', headers=auth(token)).status_code == 401


def test_cookie_auth_requires_csrf_header(client, app):
    make_user('alice')
    login(client, 'alice')  # sets the access and csrf cookies on the test client

    assert client.post('/api/post', json={'title': 't', 'content': 'c'}).status_code == 401

    csrf = client.get_cookie('csrf_access_token').value
    resp = client.post('/api/post', json={'title': 't', 'content': 'c'}, headers={'X-CSRF-TOKEN': csrf})
    assert resp.status_code == 201


def test_confirmation_token_cannot_reset_password(client, outbox):
    client.post('/register', json={'username': 'alice', 'email': 'alice@example.com', 'password': PASSWORD})
    confirm = link_token(outbox[0])

    resp = client.post('/reset/password/' + confirm, json={'password': 'attacker-password'})

    assert resp.status_code == 400


def test_reset_token_is_single_use_and_kills_old_sessions(client, app, outbox):
    make_user('alice')
    old_token = login(client, 'alice')

    assert client.post('/send/token', json={'email': 'alice@example.com'}).status_code == 200
    reset = reset_token(outbox[0])
    assert reset == link_token(outbox[0])

    assert client.post('/reset/password/' + reset, json={'password': 'brand-new-password'}).status_code == 200
    assert client.post('/reset/password/' + reset, json={'password': 'another-password'}).status_code == 400

    assert client.get('/unconfirmed', headers=auth(old_token)).status_code == 401
    login(client, 'alice', 'brand-new-password')


def test_reset_request_does_not_reveal_unknown_email(client, outbox):
    resp = client.post('/send/token', json={'email': 'ghost@example.com'})

    assert resp.status_code == 200
    assert len(outbox) == 0


def test_refresh_token_issues_new_access_token(client, app):
    make_user('alice')
    refresh = client.post('/login', json={'username': 'alice', 'password': PASSWORD}).get_json()['refresh_token']

    resp = client.post('/token/refresh', headers=auth(refresh))

    assert resp.status_code == 200
    assert client.get('/unconfirmed', headers=auth(resp.get_json()['access_token'])).status_code == 200


def test_security_headers(client):
    resp = client.get('/api/categories')

    assert resp.headers['X-Content-Type-Options'] == 'nosniff'
    assert resp.headers['X-Frame-Options'] == 'DENY'


def test_app_refuses_to_start_with_placeholder_secrets():
    with pytest.raises(RuntimeError):
        create_app({'SECRET_KEY': 'secret-key-here', 'JWT_SECRET_KEY': 'x', 'SECURITY_PASSWORD_SALT': 'y'})
