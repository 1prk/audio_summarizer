import os
import platform
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-this'
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or os.environ.get('DATABASE_URL_SQLITE') or 'sqlite:///audio_summarizer.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis Configuration - Platform specific
    IS_WINDOWS = platform.system().lower() == 'windows'
    
    if IS_WINDOWS and not os.environ.get('FORCE_REDIS'):
        # Use in-memory fallback for Windows
        REDIS_URL = 'memory://'
        USE_REDIS_FALLBACK = True
    else:
        # Use Redis for Linux/Docker or when explicitly forced
        REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
        USE_REDIS_FALLBACK = False
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # Whisper Configuration
    WHISPER_MODEL = os.environ.get('WHISPER_MODEL') or 'tiny'
    WHISPER_DEVICE = os.environ.get('WHISPER_DEVICE') or 'cpu'
    
    # Storage Configuration
    AUDIO_STORAGE_PATH = os.environ.get('AUDIO_STORAGE_PATH') or './data/audio'
    TRANSCRIPT_STORAGE_PATH = os.environ.get('TRANSCRIPT_STORAGE_PATH') or './data/transcripts'
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FORMAT = os.environ.get('LOG_FORMAT') or '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Celery Configuration - Platform specific
    if IS_WINDOWS and not os.environ.get('FORCE_REDIS'):
        # Use in-memory fallback for Windows
        CELERY_BROKER_URL = 'memory://'
        CELERY_RESULT_BACKEND = 'memory://'
    else:
        # Use Redis for Linux/Docker or when explicitly forced
        CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
        CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'
    
    # App Configuration
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH') or 16777216)  # 16MB
    UPLOAD_TIMEOUT = int(os.environ.get('UPLOAD_TIMEOUT') or 3600)  # 1 hour


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_ENV = 'development'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    FLASK_ENV = 'production'


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}