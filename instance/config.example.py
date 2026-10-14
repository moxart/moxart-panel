# Copy to instance/config.py and fill in. Any key can also be set as an
# environment variable prefixed with MOXART_, e.g. MOXART_SECRET_KEY.
# Generate secrets with: python3 -c "import secrets; print(secrets.token_urlsafe(48))"
import os

SECRET_KEY = ''
SECURITY_PASSWORD_SALT = ''
JWT_SECRET_KEY = ''

SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://moxart:password@localhost/moxart'

JWT_TOKEN_LOCATION = ['headers', 'cookies']
JWT_COOKIE_CSRF_PROTECT = True
# set to True when serving over HTTPS
JWT_COOKIE_SECURE = False

# used to build the links inside confirmation and password reset emails
SERVER_BASE_URL = 'http://localhost:5000'

ADMIN_USERNAME = 'moxart'
ADMIN_PASSWORD = ''
ADMIN_EMAIL = 'your gmail address'

MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USERNAME = 'your gmail address'
# For MAIL_PASSWORD use a Google account app password (16 characters)
MAIL_PASSWORD = ''
MAIL_DEFAULT_SENDER = 'sender gmail address'
MAIL_USE_TLS = True
MAIL_USE_SSL = False

UPLOAD_BASE_PATH = os.path.join('./', 'uploads/')
UPLOAD_VALID_FILE = ['.jpg', '.jpeg', '.png', '.gif', '.zip', '.tar.gz', '.rar']
