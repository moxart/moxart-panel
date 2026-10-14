import logging

from flask import current_app, render_template
from flask_mail import Message

from moxart import mail
from moxart.utils.token import generate_confirmation_token, generate_reset_token

log = logging.getLogger(__name__)


def send_confirmation_email(user):
    link = '{}/confirm/{}'.format(current_app.config['SERVER_BASE_URL'], generate_confirmation_token(user.email))

    return _send(user.email, 'Email Confirmation', 'layouts/email/confirm.html', username=user.username, link=link)


def send_reset_email(user):
    token = generate_reset_token(user)
    endpoint = '{}/reset/password/{}'.format(current_app.config['SERVER_BASE_URL'], token)

    return _send(user.email, 'Please Reset Your Password', 'layouts/email/send-reset-link.html',
                 username=user.username, token=token, endpoint=endpoint)


def _send(recipient, subject, template, **context):
    message = Message(subject, sender=current_app.config.get('MAIL_DEFAULT_SENDER'), recipients=[recipient])
    message.html = render_template(template, **context)

    try:
        mail.send(message)
    except Exception:
        log.exception('could not send "%s" email', subject)
        return False

    return True
