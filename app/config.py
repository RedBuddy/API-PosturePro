import os
import tempfile

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024
    MEDIA_DIR = os.path.join(tempfile.gettempdir(), 'analyzer_media')

class DevConfig(Config):
    DEBUG = True