from flask import Blueprint, send_from_directory, current_app

media_bp = Blueprint('media', __name__)

@media_bp.route('/<path:filename>', methods=['GET'])
def serve_media(filename):
    return send_from_directory(current_app.config['MEDIA_DIR'], filename, mimetype='video/mp4')