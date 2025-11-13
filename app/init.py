import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from .extensions import db

def create_app():
    load_dotenv()

    app = Flask(__name__)
    project_root = os.path.dirname(os.path.abspath(os.path.join(__file__, '..')))

    # MEDIA_DIR: si viene relativo en .env (p. ej. "media"), resolver contra la raíz del proyecto
    md = os.environ.get('MEDIA_DIR')
    if md and not os.path.isabs(md):
        md = os.path.join(project_root, md)
    media_dir = md or os.path.join(project_root, 'media')
    # No crear el directorio en disco; se mantiene sólo por compatibilidad de config

    # DB URL solo desde entorno
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise RuntimeError("DATABASE_URL no está definido en las variables de entorno")

    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret'),
        MAX_CONTENT_LENGTH=100 * 1024 * 1024,  # 100 MB
        MEDIA_DIR=media_dir,
        USERS_FILE=os.path.join(project_root, 'users.json'),
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
    )

    CORS(app)
    db.init_app(app)

    # Blueprints (tus rutas)
    from .routes.api import api_bp
    from .routes.auth import auth_bp
    from .routes.media import media_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(media_bp, url_prefix="/media")

    with app.app_context():
        from .models import User, SessionToken, PasswordResetToken  # noqa
        db.create_all()

    return app