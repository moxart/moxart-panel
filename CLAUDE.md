# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Moxart Panel is a blog/admin panel built as a Flask JSON API backed by MySQL (`moxart/`). The project is unfinished. It runs on Flask 3, Flask-JWT-Extended 4, Flask-SQLAlchemy 3 / SQLAlchemy 2 (`db.select(...)` style, not `Model.query`), and marshmallow 4. The MySQL driver is PyMySQL (`mysql+pymysql://`).

## Commands

```bash
make start                               # Docker: writes .env with random secrets, starts MySQL + API + Mailpit, seeds data
make down / make logs                    # stop (data kept) / follow API logs
make manage CMD=show-users               # run a manage.py command inside the app container
make install && make test                # local venv + pytest (in-memory SQLite, mail suppressed, no Docker needed)
venv/bin/python -m pytest tests/test_auth.py::test_logout_revokes_token   # single test
./init.sh                                # local MySQL: prompts for creds, creates DB, runs init-db + bootstrap; no mysql client -> runs make start
flask run                                # .flaskenv sets FLASK_APP=moxart, FLASK_DEBUG=1; serves on :5000
```

To try the CLI or server without MySQL, set `MOXART_SQLALCHEMY_DATABASE_URI=sqlite:///some.db` and `MOXART_MAIL_SUPPRESS_SEND=true`.

## Architecture

- **Config**: `create_app` in `moxart/__init__.py` loads config in this order: defaults, then `instance/config.py` (git-ignored; template in `instance/config.example.py`), then `MOXART_*` environment variables. Tests skip the last two steps and pass a mapping instead. It refuses to start without `SECRET_KEY`, `JWT_SECRET_KEY` and `SECURITY_PASSWORD_SALT`. Values in `instance/config.py` override the defaults, so security defaults such as `JWT_COOKIE_CSRF_PROTECT` must not be turned off there.
- **App wiring**: models, `errors.py` (handlers that return JSON for every error) and `jwt_callbacks.py` are imported inside `create_app`. New blueprints must be registered there too. A global `after_request` hook adds security headers.
- **Auth**: the JWT identity is `user.user_public_id`. Pass a `User` to `create_access_token(identity=user)`, and read the logged-in user through `flask_jwt_extended.current_user`, which is loaded from the database on every request. Tokens are accepted from the `Authorization` header or from cookies. Cookie requests need the `X-CSRF-TOKEN` header on writes. Each token carries a `pwd` claim, an HMAC fingerprint of the password hash, so changing the password invalidates every existing token. Logout writes the token's `jti` to the `token_blocklist` table.
- **Authorization**: `moxart/utils/decorator.py` provides `admin_required` and `confirmed_required`, which check `current_user` in the database rather than the token claims. Ownership rules live in `moxart/services.py`: `can_manage` allows the user themselves or an admin. Business logic shared by routes and `manage.py` (user update/delete, HTML sanitizing with nh3, unique slugs) also lives in `services.py`.
- **Signed links**: `moxart/utils/token.py` uses a separate itsdangerous salt per purpose (email confirmation vs password reset). Reset tokens include the password fingerprint, so each one works only once. Email links are built from `SERVER_BASE_URL`. The reset email carries the raw token for `POST /reset/password/<token>`, since there is no frontend.
- **Input**: use `json_body()` and `required_fields()` from `moxart/utils/request.py`, plus the `validate_*` helpers in `moxart/utils/security.py`. Raising `ValidationError` produces a 400 JSON response.
- **Models**: entities are related through UUID string `*_public_id` columns rather than the integer PKs, and only public IDs are exposed. `User.admin` is the source of truth for admin rights. The `Role` rows (1 = admin, 2 = guest) are written but not read. Never add `password` to a schema.
- **Schema management**: `manage.py init-db` creates tables with `db.create_all()`. That only creates missing tables and never alters existing ones. There is no `migrations/` directory.
- **Uploads**: files go to `UPLOAD_BASE_PATH/<username>/<YYYY>/<MM>/` with a random filename prefix. Usernames are restricted to `[A-Za-z0-9_.-]`, and `user_upload_dir` rejects any path outside the base directory. Renaming a user moves their directory.
- **Rate limits**: Flask-Limiter applies per-route limits to login, register and the reset/confirm endpoints. Storage is in memory by default (`RATELIMIT_STORAGE_URI`), and tests disable it.
- **`manage.py`**: a standalone Click group, separate from the `flask` CLI, that pushes an app context at import time. `bootstrap` is idempotent, while the individual `init-*` commands fail if their data already exists.
- **Docker**: in the container, configuration comes only from `.env` and the `MOXART_*` variables in `docker-compose.yml` (`instance/config.py` is excluded by `.dockerignore`). The entrypoint runs `init-db` before gunicorn starts. Gunicorn runs one worker with threads so the in-memory rate limits stay accurate. Email goes to the Mailpit container. Only ports 5000 (API) and 8025 (Mailpit) are published, both on 127.0.0.1.
