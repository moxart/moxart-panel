import io
import os

from moxart import db
from moxart.models.category import Category
from moxart.models.post import Post
from moxart.models.user import User
from tests.conftest import PASSWORD, auth, login, make_user


def test_user_listings_require_admin_and_hide_password_hash(client, app):
    make_user('alice')
    make_user('root', admin=True)

    assert client.get('/dashboard/users').status_code == 401
    assert client.get('/dashboard/users', headers=auth(login(client, 'alice'))).status_code == 403

    admin = auth(login(client, 'root'))
    for resp in (client.get('/dashboard/users', headers=admin), client.post('/api/users', headers=admin)):
        assert resp.status_code == 200
        assert 'password' not in resp.get_data(as_text=True)


def test_other_users_see_only_public_profile(client, app):
    bob = make_user('bob')
    make_user('alice')

    data = client.get('/api/user/' + bob.user_public_id, headers=auth(login(client, 'alice'))).get_json()['data']

    assert 'email' not in data
    assert data['username'] == 'bob'


def test_user_cannot_edit_or_delete_someone_else(client, app):
    bob = make_user('bob')
    make_user('alice')
    alice = auth(login(client, 'alice'))

    assert client.put('/api/user/' + bob.user_public_id, json={'password': 'hijacked-pass'}).status_code == 401
    assert client.put('/api/user/' + bob.user_public_id, json={'password': 'hijacked-pass'},
                      headers=alice).status_code == 403
    assert client.delete('/api/user/' + bob.user_public_id, headers=alice).status_code == 403


def test_password_change_requires_current_password(client, app):
    alice = make_user('alice')
    token = auth(login(client, 'alice'))
    url = '/api/user/' + alice.user_public_id

    assert client.put(url, json={'password': 'new-password-1'}, headers=token).status_code == 400

    resp = client.put(url, json={'password': 'new-password-1', 'current_password': PASSWORD}, headers=token)
    assert resp.status_code == 200
    assert resp.get_json()['relogin_required'] is True
    assert client.get(url, headers=token).status_code == 401


def test_partial_profile_update_keeps_other_fields(client, app):
    alice = make_user('alice')
    token = auth(login(client, 'alice'))

    resp = client.put('/api/user/' + alice.user_public_id, json={'bio': 'hello', 'first_name': 'Alice'},
                      headers=token)

    assert resp.status_code == 200
    user = db.session.get(User, alice.id)
    assert user.profile.bio == 'hello'
    assert user.username == 'alice' and user.email == 'alice@example.com'


def test_rename_moves_upload_directory(client, app):
    alice = make_user('alice')
    token = auth(login(client, 'alice'))
    base = app.config['UPLOAD_BASE_PATH']
    os.makedirs(os.path.join(base, 'alice'))

    client.put('/api/user/' + alice.user_public_id, json={'username': 'alicia'}, headers=token)

    assert os.path.isdir(os.path.join(base, 'alicia'))
    assert not os.path.exists(os.path.join(base, 'alice'))
    # tokens are tied to the public id, so the session survives the rename
    assert client.get('/unconfirmed', headers=token).status_code == 200


def test_create_post_uses_logged_in_author_and_sanitizes(client, app):
    alice = make_user('alice')
    bob = make_user('bob')
    token = auth(login(client, 'alice'))

    resp = client.post('/api/post', headers=token, json={
        'user_public_id': bob.user_public_id,
        'title': 'Hello',
        'content': '<p onclick="steal()">hi</p><script>alert(1)</script>',
    })
    assert resp.status_code == 201

    post = db.session.execute(db.select(Post)).scalar_one()
    assert post.user_public_id == alice.user_public_id
    assert post.title == 'Hello'
    assert 'script' not in post.content and 'onclick' not in post.content


def test_duplicate_titles_get_unique_slugs(client, app):
    make_user('alice')
    token = auth(login(client, 'alice'))

    for _ in range(2):
        assert client.post('/api/post', json={'title': 'Same', 'content': 'x'}, headers=token).status_code == 201

    assert {post['title_slug'] for post in client.get('/api/posts').get_json()['data']} == {'same', 'same-2'}


def test_unconfirmed_user_cannot_post(client, app):
    make_user('alice', confirmed=False)

    resp = client.post('/api/post', json={'title': 't', 'content': 'c'}, headers=auth(login(client, 'alice')))

    assert resp.status_code == 401


def test_only_author_or_admin_deletes_post(client, app):
    make_user('alice')
    make_user('bob')
    make_user('root', admin=True)
    post_id = client.post('/api/post', json={'title': 't', 'content': 'c'},
                          headers=auth(login(client, 'alice'))).get_json()['post_public_id']

    assert client.delete('/api/post/' + post_id).status_code == 401
    assert client.delete('/api/post/' + post_id, headers=auth(login(client, 'bob'))).status_code == 403
    assert client.delete('/api/post/' + post_id, headers=auth(login(client, 'root'))).status_code == 200


def test_author_edits_post_partially(client, app):
    make_user('alice')
    token = auth(login(client, 'alice'))
    post_id = client.post('/api/post', json={'title': 'Old title', 'content': 'old'},
                          headers=token).get_json()['post_public_id']
    news = Category(category_name='News')
    db.session.add(news)
    db.session.commit()
    news_id = news.category_public_id

    resp = client.put('/api/post/' + post_id, headers=token, json={
        'title': 'New title',
        'content': '<p>new</p><script>alert(1)</script>',
        'category_public_id': news_id,
    })

    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['title'] == 'New title'
    assert data['category_public_id'] == news_id
    assert 'script' not in data['content'] and '<p>new</p>' in data['content']
    # the slug is kept so existing links still work
    assert data['title_slug'] == 'old-title'

    resp = client.put('/api/post/' + post_id, headers=token, json={'content': 'only content'})
    assert resp.status_code == 200
    assert resp.get_json()['data']['title'] == 'New title'


def test_only_author_or_admin_edits_post(client, app):
    make_user('alice')
    make_user('bob')
    make_user('root', admin=True)
    post_id = client.post('/api/post', json={'title': 't', 'content': 'c'},
                          headers=auth(login(client, 'alice'))).get_json()['post_public_id']
    body = {'content': 'edited'}

    assert client.put('/api/post/' + post_id, json=body).status_code == 401
    assert client.put('/api/post/' + post_id, json=body, headers=auth(login(client, 'bob'))).status_code == 403
    assert client.put('/api/post/' + post_id, json=body, headers=auth(login(client, 'root'))).status_code == 200


def test_edit_post_rejects_bad_input(client, app):
    make_user('alice')
    token = auth(login(client, 'alice'))
    post_id = client.post('/api/post', json={'title': 't', 'content': 'c'},
                          headers=token).get_json()['post_public_id']

    for body in ({}, {'unknown': 'x'}, {'title': 'x' * 256}, {'content': 5},
                 {'category_public_id': '00000000-0000-0000-0000-000000000000'}):
        assert client.put('/api/post/' + post_id, json=body, headers=token).status_code == 400

    assert client.put('/api/post/missing', json={'content': 'x'}, headers=token).status_code == 404


def test_category_creation_is_admin_only(client, app):
    make_user('alice')
    make_user('root', admin=True)

    assert client.post('/api/category', json={'category_name': 'News'},
                       headers=auth(login(client, 'alice'))).status_code == 403

    admin = auth(login(client, 'root'))
    resp = client.post('/api/category', json={'category_name': 'News'}, headers=admin)
    assert resp.status_code == 201
    assert client.get('/api/category/' + resp.get_json()['category_public_id']).status_code == 200
    assert client.post('/api/category', json={'category_name': 'News'}, headers=admin).status_code == 409


def test_upload_saves_into_user_directory(client, app):
    make_user('alice')
    token = auth(login(client, 'alice'))

    resp = client.post('/upload', headers=token, data={
        'file': [(io.BytesIO(b'png'), '../../evil.png'), (io.BytesIO(b'tgz'), 'backup.tar.gz')],
    })

    assert resp.status_code == 200
    root = os.path.join(app.config['UPLOAD_BASE_PATH'], 'alice')
    saved = [name for _, _, files in os.walk(root) for name in files]
    assert len(saved) == 2
    assert any(name.endswith('evil.png') for name in saved)


def test_upload_rejects_bad_extension(client, app):
    make_user('alice')

    resp = client.post('/upload', headers=auth(login(client, 'alice')),
                       data={'file': (io.BytesIO(b'x'), 'shell.php')})

    assert resp.status_code == 400


def test_unknown_routes_return_json(client):
    resp = client.get('/nope')

    assert resp.status_code == 404
    assert resp.get_json()['status'] == 404


def _publish(client, token, *titles):
    for title in titles:
        assert client.post('/api/post', json={'title': title, 'content': 'x'}, headers=token).status_code == 201


def test_posts_are_paginated(client, app):
    make_user('alice')
    _publish(client, auth(login(client, 'alice')), *['Post {}'.format(i) for i in range(5)])

    first = client.get('/api/posts?per_page=2').get_json()
    last = client.get('/api/posts?per_page=2&page=3').get_json()
    beyond = client.get('/api/posts?per_page=2&page=9').get_json()

    assert first['pagination'] == {'page': 1, 'per_page': 2, 'total': 5, 'pages': 3}
    assert len(first['data']) == 2 and len(last['data']) == 1 and beyond['data'] == []
    seen = [post['post_public_id'] for page in range(1, 4)
            for post in client.get('/api/posts?per_page=2&page={}'.format(page)).get_json()['data']]
    assert len(set(seen)) == 5


def test_posts_pagination_defaults_and_limits(client, app):
    assert client.get('/api/posts').get_json()['pagination']['per_page'] == 20
    assert client.get('/api/posts?per_page=1000').get_json()['pagination']['per_page'] == 100

    for query in ('page=0', 'page=-1', 'page=abc', 'per_page=0'):
        assert client.get('/api/posts?' + query).status_code == 400


def test_get_post_by_slug(client, app):
    make_user('alice')
    _publish(client, auth(login(client, 'alice')), 'Hello World', 'Hello World')

    resp = client.get('/api/post/slug/hello-world-2')

    assert resp.status_code == 200
    assert resp.get_json()['data']['title_slug'] == 'hello-world-2'
    assert client.get('/api/post/slug/missing').status_code == 404
