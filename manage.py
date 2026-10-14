import shutil

import click
from sqlalchemy.exc import IntegrityError
from terminaltables import AsciiTable

from moxart import create_app, db
from moxart.models.category import Category
from moxart.models.post import Post
from moxart.models.role import Role
from moxart.models.user import User
from moxart.services import unique_post_slug
from moxart.utils.email import send_confirmation_email
from moxart.utils.security import ValidationError, hash_password, validate_email, validate_password, validate_username
from moxart.utils.upload import init_client_upload_dir, user_upload_dir

ADMIN_ROLE_ID = 1
GUEST_ROLE_ID = 2

app = create_app()
app.app_context().push()


# helpers

def create_user(username, email, password, admin):
    try:
        user = User(username=validate_username(username), email=validate_email(email),
                    password=hash_password(validate_password(password)), admin=admin, confirmed=False)
    except ValidationError as error:
        raise click.ClickException(error.msg)

    try:
        db.session.add(user)
        db.session.flush()
        db.session.add(Role(role_id=ADMIN_ROLE_ID if admin else GUEST_ROLE_ID, user_public_id=user.user_public_id))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise click.ClickException('username or email address already exists please choose another')

    init_client_upload_dir(app.config['UPLOAD_BASE_PATH'], user.username)

    if not send_confirmation_email(user):
        click.echo('warning: the confirmation email could not be sent, check the mail settings')

    click.echo('{} has been created'.format(user.username))

    return user


def find_user(**filters):
    user = db.session.execute(db.select(User).filter_by(**filters)).scalar_one_or_none()

    if user is None:
        raise click.ClickException('user not found')

    return user


def _category_by_slug(slug):
    return db.session.execute(db.select(Category).filter_by(category_name_slug=slug)).scalar_one_or_none()


def all_users(order_by):
    return db.session.execute(db.select(User).order_by(order_by)).scalars().all()


# end helpers


@click.group()
def cli():
    pass


# Initializing Database
@cli.command()
def init_db():
    db.create_all()
    click.echo('initialized database')


# Create the default category, admin user and first post; safe to run more than once
@cli.command()
@click.pass_context
def bootstrap(ctx):
    db.create_all()

    if _category_by_slug('uncategorized') is None:
        _create_category('Uncategorized')

    if db.session.execute(db.select(User).filter_by(username=app.config['ADMIN_USERNAME'])).first() is None:
        ctx.invoke(init_admin)

    if db.session.execute(db.select(Post.id)).first() is None:
        ctx.invoke(init_post)

    click.echo('bootstrap complete')


# show all users
@cli.command()
def show_users():
    users = all_users(User.registered_at)

    if not users:
        click.echo('there are no users that match your search')
        return

    rows = [['Username', 'Private ID', 'Public ID', 'Email', 'Is Admin', 'Last Activity', 'Registered At',
             'Confirmed', 'Confirmed At']]
    rows += [[user.username, user.id, user.user_public_id, user.email, user.admin, user.last_activity,
              user.registered_at, user.confirmed, user.confirmed_at] for user in users]

    click.echo(AsciiTable(rows).table)


# show all users (alternative)
@cli.command()
def show_users_alt():
    users = all_users(User.registered_at)

    if not users:
        click.echo('there are no users that match your search')
        return

    for i, user in enumerate(users, start=1):
        click.echo('*************************** No. {} ***************************'.format(i))
        click.echo('id: {}'.format(user.id))
        click.echo('public: {}'.format(user.user_public_id))
        click.echo('username: {}'.format(user.username))
        click.echo('email: {}'.format(user.email))
        click.echo('admin: {}'.format(user.admin))
        click.echo('last activity: {}'.format(user.last_activity))
        click.echo('registered at: {}'.format(user.registered_at))
        click.echo('is confirmed: {}'.format(user.confirmed))
        click.echo('confirmed at: {}'.format(user.confirmed_at))


# show user's activity
@cli.command()
def show_users_activity():
    users = all_users(User.last_activity.desc())

    if not users:
        click.echo('no activity found')
        return

    rows = [['Username', 'Last Activity']] + [[user.username, user.last_activity] for user in users]

    click.echo(AsciiTable(rows).table)


# Initializing an Admin User from the config file
@cli.command()
def init_admin():
    password = app.config.get('ADMIN_PASSWORD')

    if not password or password == 'password':
        password = click.prompt('ADMIN_PASSWORD is unset or the insecure default; choose an admin password',
                                hide_input=True, confirmation_prompt=True)

    create_user(app.config['ADMIN_USERNAME'], app.config['ADMIN_EMAIL'], password, admin=True)


# add new admin user
@cli.command()
@click.option('-a', '--username', prompt='Username', required=True)
@click.option('-e', '--email', prompt='Email', required=True)
@click.option('-p', '--password', prompt='Password', hide_input=True, confirmation_prompt=True, required=True)
def add_admin(username, email, password):
    create_user(username, email, password, admin=True)


# Initializing a User
@cli.command()
@click.option('-u', '--username', prompt='Username', required=True)
@click.option('-e', '--email', prompt='Email', required=True)
@click.option('-p', '--password', prompt='Password', hide_input=True, confirmation_prompt=True, required=True)
def init_user(username, email, password):
    create_user(username, email, password, admin=False)


# Initializing user directory
@cli.command()
@click.option('-u', '--username', prompt='Username', required=True)
def init_directory(username):
    user = find_user(username=username)

    click.echo('{} is ready'.format(init_client_upload_dir(app.config['UPLOAD_BASE_PATH'], user.username)))


# drop client directory
@cli.command()
@click.option('-u', '--username', prompt='Username', required=True)
def drop_directory(username):
    user = find_user(username=username)
    path = user_upload_dir(app.config['UPLOAD_BASE_PATH'], user.username)

    click.confirm('permanently delete {} and every file in it?'.format(path), abort=True)

    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        raise click.ClickException('directory not found')

    click.echo('directory removed completely')


# Initializing uncategorized category
@cli.command()
def init_category():
    _create_category('Uncategorized')


# Create a new category
@cli.command()
@click.option('-c', '--category', prompt='Category Name', required=True)
def add_category(category):
    _create_category(category)


def _create_category(name):
    try:
        db.session.add(Category(category_name=name))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise click.ClickException('the {} category has already been taken'.format(name))

    click.echo('{} category has been created'.format(name))


# drop category
@cli.command()
@click.option('-c', '--category', prompt='Category Name (slug)', required=True)
def drop_category(category):
    found = _category_by_slug(category)

    if found is None:
        raise click.ClickException("{} category doesn't exist".format(category))

    if found.post:
        raise click.ClickException('{} category still has posts, move or remove them first'.format(category))

    db.session.delete(found)
    db.session.commit()

    click.echo('{} category has been removed successfully from dashboard'.format(category))


# Initializing Hello World Post
@cli.command()
def init_post():
    user = find_user(username=app.config['ADMIN_USERNAME'])
    category = _category_by_slug('uncategorized')

    if category is None:
        raise click.ClickException('run init-category first')

    title = 'Hello, World!'
    db.session.add(Post(user_public_id=user.user_public_id, category_public_id=category.category_public_id,
                        title=title, title_slug=unique_post_slug(title),
                        content='<p>The Hello World post in Moxart is actually just a simple dummy post content set'
                                ' by the Moxart as a placeholder post content upon initial installation.</p>'))
    db.session.commit()

    click.echo('hello world post has been created')


# drop post
@cli.command()
@click.option('-p', '--post-public-id', prompt='Post Public ID', required=True)
def drop_post(post_public_id):
    post = db.session.execute(db.select(Post).filter_by(post_public_id=post_public_id)).scalar_one_or_none()

    if post is None:
        raise click.ClickException("{} post public id doesn't exist".format(post_public_id))

    db.session.delete(post)
    db.session.commit()

    click.echo('post has been removed successfully')


# Drop User from Dashboard
@cli.command()
@click.option('-u', '--user-public-id', prompt='User Public ID', required=True)
def drop_user(user_public_id):
    user = find_user(user_public_id=user_public_id)

    if user.admin:
        raise click.ClickException('admin users can not be dropped')

    db.session.delete(user)
    db.session.commit()

    click.echo('{} user has been removed successfully from dashboard'.format(user_public_id))


if __name__ == '__main__':
    cli()
