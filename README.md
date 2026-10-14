# Moxart Panel

A JSON API for a small blog, built with Flask and MySQL. It handles user accounts (sign-up, email confirmation, password reset), posts, categories and file uploads, with an admin role for managing users.

> **Status:** unfinished. There is no frontend yet: you talk to the API with curl, Postman or your own client. See [Not built yet](#not-built-yet).

## Contents

- [Quick start with Docker](#quick-start-with-docker)
- [Running without Docker](#running-without-docker)
- [Configuration](#configuration)
- [Using the API](#using-the-api)
- [Endpoints](#endpoints)
- [Testing with Postman](#testing-with-postman)
- [Management commands](#management-commands)
- [Running the tests](#running-the-tests)
- [Not built yet](#not-built-yet)

## Quick start with Docker

You need Docker with Compose, and `make`.

```bash
make start
```

This writes a `.env` file with random secrets and a random admin password (an existing `.env` is never overwritten). It then starts MySQL, the API and [Mailpit](https://mailpit.axllent.org/), and creates the tables, an `Uncategorized` category, the `moxart` admin account and a "hello world" post.

When it finishes:

| What | Where |
| --- | --- |
| API | http://localhost:5000 |
| Mail inbox (Mailpit) | http://localhost:8025 |
| Admin login | username `moxart`, password is `MOXART_ADMIN_PASSWORD` in `.env` |

Every email the app sends lands in Mailpit. Open the confirmation email there and follow the link to confirm the admin account. Some endpoints refuse unconfirmed accounts.

Other commands:

| Command | What it does |
| --- | --- |
| `make down` | Stop the containers. Data is kept. |
| `make logs` | Follow the API logs. |
| `make manage CMD=show-users` | Run a [management command](#management-commands) in the container. |
| `make clean` | Stop the containers and **delete** the database and uploads (asks first). |
| `make help` | List all targets. |

## Running without Docker

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt    # requirements-dev.txt also installs pytest
```

1. Copy `instance/config.example.py` to `instance/config.py` and fill it in (see [Configuration](#configuration)). The file is git-ignored.
2. Set up the database with `./init.sh`. It asks for MySQL credentials, creates the database and runs `manage.py init-db` and `manage.py bootstrap`. If there is no `mysql` client installed it runs `make start` instead.
3. Start the server with `flask run`. It serves on http://localhost:5000 (`.flaskenv` sets `FLASK_APP` and debug mode).

To try it without MySQL or a mail server, use SQLite and turn off email sending:

```bash
export MOXART_SQLALCHEMY_DATABASE_URI=sqlite:///moxart.db
export MOXART_MAIL_SUPPRESS_SEND=true
python manage.py init-db && python manage.py bootstrap
flask run
```

## Configuration

Settings are read from `instance/config.py`, then from environment variables prefixed with `MOXART_` (for example `MOXART_SECRET_KEY`), which take priority. Under Docker only `.env` and `docker-compose.yml` are used.

| Setting | Notes |
| --- | --- |
| `SECRET_KEY`, `JWT_SECRET_KEY`, `SECURITY_PASSWORD_SALT` | Required. The app won't start without them. Generate each with `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `SQLALCHEMY_DATABASE_URI` | Defaults to `mysql+pymysql://moxart:password@localhost/moxart`. |
| `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Used by `bootstrap` and `init-admin` to create the first admin. The username defaults to `moxart`. If the password is empty you are asked for one. The email must be a real address. |
| `MAIL_*` | SMTP settings. Email is needed for account confirmation and password resets. For Gmail, use an app password. |
| `SERVER_BASE_URL` | Base of the links in emails. Defaults to `http://localhost:5000`. |
| `JWT_COOKIE_SECURE` | Set to `True` when serving over HTTPS. |
| `UPLOAD_BASE_PATH`, `UPLOAD_VALID_FILE` | Where uploads are stored and which extensions are allowed. |

## Using the API

Log in to get tokens:

```bash
curl -H "Content-Type: application/json" \
  -d '{"username": "moxart", "password": "<your admin password>"}' \
  http://localhost:5000/login
```

```json
{
  "status": 200,
  "login": true,
  "msg": "user has been authenticated successfully",
  "access_token": "eyJ0eXAiOiJKV1Qi...",
  "refresh_token": "eyJ0eXAiOiJKV1Qi..."
}
```

Send the access token on later requests:

```bash
curl -H "Authorization: Bearer <access_token>" http://localhost:5000/unconfirmed
```

How sessions work:

- Access tokens last one hour. Get a new one with `POST /token/refresh`, sending the refresh token (valid for 30 days) as the bearer token.
- `DELETE /logout` revokes the token you send.
- Changing your password logs out every existing session.
- Login also sets the tokens as cookies, for browser clients. Cookie-authenticated `POST`, `PUT` and `DELETE` requests must copy the `csrf_access_token` cookie into an `X-CSRF-TOKEN` header.
- Every response is JSON, errors included, with a `status` and a `msg`.

Login is limited to 10 attempts a minute and registration to 10 an hour. The confirmation and password reset endpoints have limits too.

## Endpoints

**Auth** is what the request needs: *none*, *login* (any valid token), *confirmed* (a token for a confirmed account) or *admin*.

### Accounts

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/register` | none | Create an account (`username`, `email`, `password` of 8+ characters). Sends a confirmation email and returns tokens. |
| POST | `/login` | none | Log in with `username` and `password`. |
| POST | `/token/refresh` | refresh token | Get a new access token. |
| DELETE | `/logout` | login | Revoke the current token. |
| GET | `/confirm/<token>` | none | Confirm an email address using the token from the email. |
| GET | `/unconfirmed` | login | Check whether your account is confirmed. |
| POST | `/resend/confirm` | login | Send the confirmation email again. |
| POST | `/send/token` | none | Email a password reset token to `email`. Always answers 200. |
| POST | `/reset/password/<token>` | none | Set a new `password`. Each reset token works once. |

### Users

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/users` | admin | List all users. |
| GET | `/api/user/<user_public_id>` | confirmed | Get a user. Other users only see the public fields. |
| PUT | `/api/user/<user_public_id>` | confirmed | Update yourself (or anyone, as admin). Accepts `username`, `email`, `password` (with `current_password` unless admin) and the profile fields `first_name`, `last_name`, `nickname`, `url`, `bio`, `location`, `display_name`. A new email has to be confirmed again. |
| DELETE | `/api/user/<user_public_id>` | confirmed | Delete yourself (or anyone, as admin). |
| GET | `/dashboard/users` | admin | List all users. |
| DELETE | `/dashboard/user/<username>` | admin | Delete a user by username. |

### Posts and categories

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/post` | confirmed | Publish a post (`title`, `content`, optional `category_public_id`; defaults to Uncategorized). |
| PUT | `/api/post/<post_public_id>` | confirmed | Edit your post (or any, as admin). Send any of `title`, `content`, `category_public_id`. The URL slug stays the same. |
| DELETE | `/api/post/<post_public_id>` | login | Delete your post (or any, as admin). |
| GET | `/api/post/<post_public_id>` | none | Get a post. |
| GET | `/api/post/slug/<slug>` | none | Get a post by its URL slug. |
| GET | `/api/posts?page=1&per_page=20` | none | List posts, newest first. `per_page` is capped at 100. |
| POST | `/api/category` | admin | Create a category (`category_name`). |
| GET | `/api/category/<category_public_id>` | none | Get a category. |
| GET | `/api/categories` | none | List categories. |

Post content can contain HTML. Scripts, event handlers and unsafe links are stripped.

### Uploads

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/upload` | confirmed | Upload one or more files as multipart form field `file`. Allowed: `.jpg`, `.jpeg`, `.png`, `.gif`, `.zip`, `.tar.gz`, `.rar`, up to 16 MB per request. |

Files are saved under `UPLOAD_BASE_PATH/<username>/<year>/<month>/` with a random prefix on the name.

## Testing with Postman

Import `postman/moxart.postman_collection.json` (**Import** in Postman, then pick the file). It has a request for every endpoint, in the same groups as above.

1. On the collection's **Variables** tab, set `password`, and `username` if you aren't logging in as `moxart`. `base_url` defaults to `http://localhost:5000`.
2. Send **Auth → Login**. It saves the tokens, and every other request uses them from then on. When the access token expires, send **Auth → Refresh access token**.
3. Some requests save IDs for later ones: **List users (admin)** saves `user_public_id`, **Create category** saves `category_public_id`, and **Create post** saves `post_public_id` and `post_slug`.
4. Confirmation and reset tokens arrive by email. Paste them into the `confirm_token` and `reset_token` variables.

Be careful with **Dashboard → Delete user by username**: it uses the `username` variable, which is your own login unless you change it first.

To run the collection from the command line with [newman](https://github.com/postmanlabs/newman), run it in a single `newman run`. Variables saved by one request don't carry over between separate runs, so the login token would be lost.

## Management commands

`manage.py` has commands for setting up and inspecting the database. Run them with `python manage.py <command>` locally or `make manage CMD=<command>` under Docker. Commands that need input ask for it, or take options such as `-u <username>`.

| Command | What it does |
| --- | --- |
| `init-db` | Create any missing tables. It never changes existing tables. |
| `bootstrap` | Create the Uncategorized category, the admin from the config and a hello world post. Safe to run again. |
| `init-admin` | Create the admin from the config. |
| `add-admin` | Create another admin. |
| `init-user` | Create a regular user. |
| `drop-user` | Delete a user by public ID. |
| `show-users`, `show-users-alt` | List users. |
| `show-users-activity` | Show each user's last activity. |
| `init-category` | Create the Uncategorized category. |
| `add-category` | Create a category. |
| `drop-category` | Delete a category by slug. |
| `init-post` | Create the hello world post. |
| `drop-post` | Delete a post by public ID. |
| `init-directory`, `drop-directory` | Create or delete a user's upload directory. |

The `init-*` commands fail if their data already exists. Use `bootstrap` when you aren't sure.

## Running the tests

```bash
make install    # creates venv/ with the dev dependencies
make test
```

The tests use an in-memory SQLite database and don't send email, so they need neither MySQL nor Docker. To run one test:

```bash
venv/bin/python -m pytest tests/test_auth.py::test_logout_revokes_token
```

## Not built yet

- A frontend. "Dashboard" is a group of JSON endpoints, not a UI.
- Comments. The table exists and posts have a `comment_count`, but there are no endpoints.
- Renaming or deleting categories through the API (`manage.py drop-category` works).
- Reading profile fields back. They can be saved but no endpoint returns them.
- Listing or downloading uploaded files.
- Filtering posts by author or category, search, and drafts.
- Database migrations. `init-db` only creates missing tables, so schema changes to existing tables have to be applied by hand.
