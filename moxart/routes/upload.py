import os
import uuid

from flask import current_app, Blueprint, request, jsonify
from flask_jwt_extended import current_user
from werkzeug.utils import secure_filename

from moxart.utils.decorator import confirmed_required
from moxart.utils.time import utcnow
from moxart.utils.upload import user_upload_dir

bp = Blueprint('upload', __name__)


@bp.route('/upload', methods=['POST'])
@confirmed_required
def upload_file():
    files = [file for file in request.files.getlist('file') if file.filename]

    if not files:
        return jsonify(status=400, msg='no file was uploaded'), 400

    valid_exts = tuple(ext.lower() for ext in current_app.config['UPLOAD_VALID_FILE'])
    filenames = [secure_filename(file.filename) for file in files]

    # validate the whole batch first so a bad file doesn't leave a partial upload behind
    if any(not name or not name.lower().endswith(valid_exts) for name in filenames):
        return jsonify(status=400, msg='some uploaded files has not valid type'), 400

    save_dir = os.path.join(user_upload_dir(current_app.config['UPLOAD_BASE_PATH'], current_user.username),
                            utcnow().strftime('%Y'), utcnow().strftime('%m'))
    os.makedirs(save_dir, exist_ok=True)

    saved = []
    for file, name in zip(files, filenames):
        # prefix keeps two uploads with the same name from overwriting each other
        unique_name = '{}-{}'.format(uuid.uuid4().hex[:8], name)
        file.save(os.path.join(save_dir, unique_name))
        saved.append(unique_name)

    return jsonify(status=200, msg='file has been uploaded successfully', files=saved), 200
