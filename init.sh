#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v mysql >/dev/null; then
    if command -v docker >/dev/null && docker compose version >/dev/null 2>&1; then
        echo 'no local mysql client found; setting up with MySQL in Docker instead'
        exec make start
    fi

    echo 'init.sh needs either a local MySQL install (mysql client + server) or Docker with Compose.' >&2
    echo 'Install one of them, e.g. `sudo apt install mysql-server`, then run ./init.sh again.' >&2
    exit 1
fi

read -rp 'MySQL USERNAME: ' MYSQL_USER
read -rsp 'MySQL PASSWORD: ' MYSQL_PASS
echo
read -rp 'MySQL Database Name: ' MYSQL_DB_NAME

if [[ ! "$MYSQL_DB_NAME" =~ ^[A-Za-z0-9_]+$ ]]; then
    echo 'database name may only contain letters, digits and underscores' >&2
    exit 1
fi

# MYSQL_PWD keeps the password out of the process list
MYSQL_PWD="$MYSQL_PASS" mysql -u"$MYSQL_USER" -e "CREATE DATABASE IF NOT EXISTS \`$MYSQL_DB_NAME\` CHARACTER SET utf8mb4;"
unset MYSQL_PASS

PYTHON="${PYTHON:-$( [ -x venv/bin/python ] && echo venv/bin/python || command -v python3 )}"

"$PYTHON" manage.py init-db
"$PYTHON" manage.py bootstrap
