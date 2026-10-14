from flask import request

from moxart.utils.security import ValidationError


def json_body():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        raise ValidationError('request body should be json format')

    return data


def required_fields(data, *names):
    values = [data.get(name) for name in names]

    if any(value is None or value == '' for value in values):
        raise ValidationError('some arguments missing')

    return values
