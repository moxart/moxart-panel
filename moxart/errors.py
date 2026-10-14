import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from moxart import db
from moxart.utils.security import ValidationError

log = logging.getLogger(__name__)


def register(app):
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return jsonify(status=400, msg=error.msg), 400

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify(status=error.code, msg=error.description), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        db.session.rollback()
        log.exception('unhandled error')

        return jsonify(status=500, msg='internal server error'), 500
