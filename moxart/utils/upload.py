import os

from moxart.utils.security import validate_username


def user_upload_dir(base_dir, username):
    validate_username(username)

    base = os.path.realpath(base_dir)
    path = os.path.realpath(os.path.join(base, username))

    if os.path.commonpath([base, path]) != base:
        raise ValueError('upload directory escapes the upload base path')

    return path


# initializing user upload directory
def init_client_upload_dir(base_dir, username):
    path = user_upload_dir(base_dir, username)
    os.makedirs(path, exist_ok=True)

    return path
