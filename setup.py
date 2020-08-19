import os
import shutil
import click
import uuid

from flask import request, render_template, jsonify
from datetime import datetime
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError
from slugify import slugify

from moxart import create_app, db

from moxart.utils.email import send_verification_link
from moxart.utils.upload import init_client_upload_dir

from moxart.models.user import User
from moxart.models.post import Post
from moxart.models.category import Category

app = create_app()
app.app_context().push()


@click.group()
def cli():
    pass


# Initializing Database
@click.command()
def init_db():
    db.create_all()
    click.echo('initialized database')


# Initializing an Admin User
@click.command()
def init_admin():
    try:
        hashed_password = generate_password_hash(app.config['ADMIN_PASSWORD'], method='sha256')

        admin = User(username=app.config['ADMIN_USERNAME'], email=app.config['ADMIN_EMAIL'],
                     password=hashed_password, admin=True, confirmed=True)

        db.session.add(admin)
        db.session.commit()

        init_client_upload_dir(app.config['UPLOAD_BASE_PATH'], admin.username)

        send_verification_link(app.config['ADMIN_EMAIL'], 'Email Confirmation',
                               app.config['MAIL_DEFAULT_SENDER'],
                               'layouts/email/confirm.html', admin.username)

    except IntegrityError:
        db.session.rollback()
        click.echo('the init-admin command has been executed before')


# add new admin user
@click.command()
@click.option('-a', '--username', prompt="Username", required=True)
@click.option('-e', '--email', prompt='Email', required=True)
@click.option('-p', '--password', prompt='Password', hide_input=True, confirmation_prompt=True, required=True)
def add_admin(username, email, password):
    try:
        hashed_password = generate_password_hash(password, method='sha256')

        admin = User(username=username, email=email, password=hashed_password, admin=True, confirmed=False)

        db.session.add(admin)
        db.session.commit()

        init_client_upload_dir(app.config['UPLOAD_BASE_PATH'], admin.username)

        send_verification_link(app.config['ADMIN_EMAIL'], 'Email Confirmation',
                               app.config['MAIL_DEFAULT_SENDER'],
                               'layouts/email/confirm.html', admin.username)

    except IntegrityError:
        db.session.rollback()
        click.echo('this user already exists')


# Initializing a User
@click.command()
@click.option('-u', '--username', prompt='Username', required=True)
@click.option('-e', '--email', prompt='Email', required=True)
@click.option('-p', '--password', prompt='Password', hide_input=True, confirmation_prompt=True, required=True)
def init_user(username, email, password):
    try:
        hashed_password = generate_password_hash(password, method='sha256')

        user = User(username=username, email=email, password=hashed_password, admin=False, confirmed=False)

        db.session.add(user)
        db.session.commit()

        init_client_upload_dir(app.config['UPLOAD_BASE_PATH'], user.username)

        send_verification_link(app.config['ADMIN_EMAIL'], 'Email Confirmation',
                               app.config['MAIL_DEFAULT_SENDER'],
                               'layouts/email/confirm.html', user.username)

    except IntegrityError:
        db.session.rollback()
        click.echo('username or email address already exists please choose another'.format(username))


# Initializing user directory
@click.command()
@click.option('-u', '--username', prompt='Username', required=True)
def init_directory(username):
    try:
        user = User.query.filter_by(username=username).first()
        os.makedirs(os.path.join(app.config['UPLOAD_BASE_PATH'], user.username))
        click.echo('the current directory is now created')
    except FileExistsError:
        click.echo("current directory already exists")
    except AttributeError:
        click.echo('you dont have permission to make a directory for this user')


# drop client directory
@click.command()
@click.option('-u', '--username', prompt='Username', required=True)
def drop_directory(username):
    try:
        user = User.query.filter_by(username=username).first()
        shutil.rmtree(os.path.join(app.config['UPLOAD_BASE_PATH'], user.username))
        click.echo('directory removed completely')
    except FileNotFoundError:
        click.echo('directory not found')
    except AttributeError:
        click.echo('username not found')


# Initializing uncategorized category
@click.command()
def init_category():
    try:
        category = Category(category_name="Uncategorized", category_name_slug=slugify("Uncategorized"))

        db.session.add(category)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        click.echo('the uncategorized category already been taken')


# Create a new category
@click.command()
@click.option('-c', '--category', prompt="Category Name", required=True)
def add_category(category):
    try:
        slug = slugify(category)

        cat = Category(category_name=category, category_name_slug=slug)

        db.session.add(cat)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        click.echo('the {} has already been taken'.format(category))


# drop category
@click.command()
@click.option('-c', '--category', prompt="Category Name (slug)", required=True)
def drop_category(category):
    if db.session.query(Category.category_name_slug).filter(Category.category_name_slug == category):
        db.session.query(Category.category_name_slug).filter(
            Category.category_name_slug == category).delete()

        db.session.commit()

        click.echo('{} category has been removed successfully from dashboard'.format(category))
    else:
        click.echo('{} category does\'nt exist'.format(category))


# Initializing Hello World Post
@click.command()
def init_post():
    try:
        user = User.query.filter_by(username=app.config["ADMIN_USERNAME"]).first()
        category = Category.query.filter_by(
            category_name_slug="uncategorized").first()

        post = Post(user_public_id=user.user_public_id, category_public_id=category.category_public_id,
                    title="Hello, World!",
                    title_slug="hello-world!",
                    content="<p>The Hello World post in Moxart is actually just a simple dummy post content set by"
                            " the Moxart as a placeholder post content upon initial installation.</p>")

        db.session.add(post)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        click.echo('there are an unexpected error in the initializing hello world post')


# drop post
@click.command()
@click.option('-p', '--post-public-id', prompt="Post Public ID", required=True)
def drop_post(post_public_id):
    try:
        post = Post.query.filter_by(post_public_id=post_public_id).first()

        db.session.delete(post)
        db.session.commit()

        click.echo('post has been removed successfully')

    except Exception:
        db.session.rollback()
        click.echo('{} post public id does\'nt exist')


# Drop User from Dashboard
@click.command()
@click.option('-u', '--user-public-id', prompt='User Public ID', required=True)
def drop_user(user_public_id):
    try:
        user = User.query.filter_by(user_public_id=user_public_id).first()

        if user and user.admin is not True:
            db.session.delete(user)
            db.session.commit()

            click.echo('{} user has been removed successfully from dashboard'.format(user_public_id))
        else:
            click.echo('dont have permission to execute this command')
    except IntegrityError:
        db.session.rollback()
        click.echo('{} user has not removed successfully from database'.format(user_public_id))


cli.add_command(init_db)
cli.add_command(init_admin)
cli.add_command(add_admin)
cli.add_command(init_user)
cli.add_command(init_directory)
cli.add_command(drop_directory)
cli.add_command(init_category)
cli.add_command(add_category)
cli.add_command(drop_category)
cli.add_command(init_post)
cli.add_command(drop_post)
cli.add_command(drop_user)

if __name__ == '__main__':
    cli()
