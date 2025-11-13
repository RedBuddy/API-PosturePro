import time
import io
from flask import Blueprint, abort, request, Response

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
        data = item['bytes']
        total = len(data)
        mime = item.get('mime', 'video/mp4')
        range_header = request.headers.get('Range')
        if range_header:
            try:
                # Example: Range: bytes=START-END
                units, rng = range_header.strip().split('=')
                if units != 'bytes':
                    raise ValueError('Unsupported unit')
                start_str, end_str = (rng.split('-') + [''])[:2]
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else total - 1
                start = max(0, min(start, total - 1))
                end = max(start, min(end, total - 1))
                chunk = data[start:end + 1]
                rv = Response(chunk, 206, mimetype=mime, direct_passthrough=True)
                rv.headers['Content-Range'] = f'bytes {start}-{end}/{total}'
                rv.headers['Accept-Ranges'] = 'bytes'
                rv.headers['Content-Length'] = str(len(chunk))
                return rv
            except Exception:
                # Fallback to full content
                pass
        # Full content
        rv = Response(data, 200, mimetype=mime, direct_passthrough=True)
        rv.headers['Accept-Ranges'] = 'bytes'
        rv.headers['Content-Length'] = str(total)
        return rv

    # Estricto: solo memoria. Si no está en caché, 404.
    return abort(404)