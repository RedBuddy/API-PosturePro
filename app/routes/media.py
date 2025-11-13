import time
import io
from flask import Blueprint, send_from_directory, current_app, send_file, abort

media_bp = Blueprint('media', __name__)

# Caché en memoria para videos analizados (no persistentes)
VIDEO_CACHE = {}

def put_in_cache(filename: str, data: bytes, mime: str = 'video/mp4', ttl: int = 600):
    """Guarda un video en caché en memoria por ttl segundos."""
    VIDEO_CACHE[filename] = {
        'bytes': data,
        'mime': mime,
        'exp': time.time() + max(1, int(ttl))
    }

@media_bp.route('/<path:filename>', methods=['GET'])
def serve_media(filename):
    # Limpiar expirados
    now = time.time()
    expired = [k for k, v in list(VIDEO_CACHE.items()) if v.get('exp', 0) < now]
    for k in expired:
        VIDEO_CACHE.pop(k, None)

    # Servir desde memoria si existe
    item = VIDEO_CACHE.get(filename)
    if item:
        buf = io.BytesIO(item['bytes'])
        buf.seek(0)
        return send_file(buf, mimetype=item.get('mime', 'video/mp4'))

    # Compatibilidad: si existe en disco, servirlo (no recomendado para analizados)
    try:
        return send_from_directory(current_app.config['MEDIA_DIR'], filename, mimetype='video/mp4')
    except Exception:
        return abort(404)