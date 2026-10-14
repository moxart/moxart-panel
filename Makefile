COMPOSE := docker compose
MANAGE := $(COMPOSE) exec app python manage.py

.PHONY: start env up bootstrap down logs manage install test clean

## start: first-time setup and run (generate .env, build, start, seed data)
start: env up bootstrap
	@echo
	@echo "API:       http://localhost:5000"
	@echo "Mail inbox: http://localhost:8025   (confirm the admin account there)"
	@echo "Admin password is MOXART_ADMIN_PASSWORD in .env"

## env: write .env with random secrets (keeps an existing one)
env:
	@python3 scripts/create_env.py

## up: build and start the containers
up:
	$(COMPOSE) up -d --build --wait

## bootstrap: create the default category, admin user and first post (idempotent)
bootstrap:
	$(MANAGE) bootstrap

## down: stop the containers (data is kept)
down:
	$(COMPOSE) down

## logs: follow the API logs
logs:
	$(COMPOSE) logs -f app

## manage: run a manage.py command, e.g. make manage CMD=show-users
manage:
	$(MANAGE) $(CMD)

## install: create a local venv with dev dependencies (for running tests outside Docker)
install:
	python3 -m venv venv
	venv/bin/pip install -r requirements-dev.txt

## test: run the test suite locally (SQLite, no Docker needed)
test:
	venv/bin/python -m pytest -q

## clean: stop the containers and DELETE the database and uploads volumes
clean:
	@read -p "This deletes the database and all uploads. Type 'yes' to continue: " answer && [ "$$answer" = yes ]
	$(COMPOSE) down -v

help:
	@grep -E '^## ' Makefile | sed 's/## //'
