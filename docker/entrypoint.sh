#!/bin/sh
set -e

# create any missing tables; existing tables and data are left alone
python manage.py init-db

exec "$@"
