import os
import time
import tempfile
import shutil
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.services.analyzer import analyzer
from app.routes.media import put_in_cache

api_bp = Blueprint('api', __name__)

LAST_PROGRESS = 0  # progreso global simple (1 usuario/proceso)

# Añade alias para evitar /api/api/progress si usas url_prefix='/api'
@api_bp.route('/progress', methods=['GET'])
@api_bp.route('/api/progress', methods=['GET'])
def get_progress():
    return jsonify({'progress': LAST_PROGRESS})

@api_bp.route('/analyze', methods=['POST'])
def api_analyze():
    global LAST_PROGRESS
    LAST_PROGRESS = 0

    try:
        if 'video' not in request.files:
            return jsonify({'message': 'Falta video'}), 400
        f = request.files['video']
        if not f.filename:
            return jsonify({'message': 'Archivo inválido'}), 400

        exercise_type = request.form.get('exercise_type', 'sentadilla')
        tipos_validos = ['sentadilla', 'desplantes', 'press_banca']
        if exercise_type not in tipos_validos:
            return jsonify({'message': f'Tipo inválido. Opciones: {tipos_validos}'}), 400

        # Guardar upload a archivo temporal
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        f.save(tmp.name)

        # Callback para ir actualizando el progreso
        def on_progress(pct: int):
            global LAST_PROGRESS           # FIX: usar global, no nonlocal
            pct = max(0, min(100, int(pct)))
            LAST_PROGRESS = pct

        # Ejecutar análisis (bloqueante)
        output_path, stats = analyzer.analizar_video_completo(
            tmp.name,
            tipo_ejercicio=exercise_type,
            on_progress=on_progress
        )

        # Forzar 100% al terminar
        LAST_PROGRESS = 100

        # Preparar respuesta vía caché en memoria (no persistente)
        ts = int(time.time())
        ext = os.path.splitext(output_path)[1] or '.mp4'
        out_name = f"analyzed_{exercise_type}_{ts}{ext}"
        mimetype = 'video/mp4' if ext.lower() == '.mp4' else 'video/x-msvideo'

        # Leer bytes del archivo procesado y eliminarlo
        try:
            with open(output_path, 'rb') as f_out:
                video_bytes = f_out.read()
        finally:
            try:
                os.unlink(output_path)
            except Exception:
                pass

        # Cargar en caché en memoria con TTL configurable
        ttl = int(os.environ.get('ANALYSIS_CACHE_TTL', '600'))
        put_in_cache(out_name, video_bytes, mime=mimetype, ttl=ttl)

        # Limpieza del archivo temporal de entrada
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

        return jsonify({'video_path': f'/media/{out_name}', 'stats': stats})
    except Exception as e:
        print(f"Error procesando video (api): {e}")
        return jsonify({'message': 'Error al analizar el video'}), 500

@api_bp.route('/health', methods=['GET'])
@api_bp.route('/api/health', methods=['GET'])
def health_check():
    # Devuelve un OK simple; puedes exponer versión o estado de servicios dependientes aquí
    return jsonify({
        'status': 'ok',
        'version': current_app.config.get('VERSION', 'dev')
    }), 200