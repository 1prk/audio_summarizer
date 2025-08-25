#!/usr/bin/env python3
"""
Windows startup script for the Audio Summarizer backend.
Automatically detects platform and uses appropriate Redis configuration.
"""

import os
import sys
import platform
import subprocess
import logging
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_platform():
    """Check if we're running on Windows."""
    system = platform.system().lower()
    logger.info(f"Detected platform: {system}")
    return system == 'windows'


def check_redis_available():
    """Check if Redis is available on the system."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        logger.info("Redis is available")
        return True
    except Exception as e:
        logger.info(f"Redis not available: {e}")
        return False


def setup_environment():
    """Set up environment variables for the application."""
    is_windows = check_platform()
    redis_available = check_redis_available()
    
    if is_windows and not redis_available:
        logger.info("Windows detected without Redis - using in-memory fallback")
        os.environ['USE_FALLBACK_REDIS'] = 'true'
        # Don't set FORCE_REDIS, let the config use fallback
    elif redis_available:
        logger.info("Redis available - using Redis backend")
        os.environ['FORCE_REDIS'] = 'true'
    else:
        logger.info("No Redis available - using in-memory fallback")
    
    # Set other environment variables if not already set
    if not os.environ.get('FLASK_ENV'):
        os.environ['FLASK_ENV'] = 'development'
    
    if not os.environ.get('SECRET_KEY'):
        os.environ['SECRET_KEY'] = 'dev-secret-key-please-change-in-production'


def start_flask_app():
    """Start the Flask application."""
    logger.info("Starting Flask application...")
    from app import create_app
    app = create_app()
    
    # Pre-load all models before starting server
    logger.info("Pre-loading models before server startup...")
    with app.app_context():
        from app.tasks import preload_all_models
        models_status = preload_all_models()
        
        ready_count = sum(models_status.values())
        total_models = len(models_status)
        
        if ready_count < total_models:
            logger.warning(f"Only {ready_count}/{total_models} models loaded successfully")
            logger.warning("Some features may not work correctly")
        else:
            logger.info("All models loaded successfully!")
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False  # Disable reloader to avoid conflicts
    )


def start_celery_worker():
    """Start Celery worker in a separate process."""
    logger.info("Starting Celery worker...")
    
    # Use subprocess to start celery worker
    cmd = [
        sys.executable, '-m', 'celery',
        '-A', 'app.celery_app.celery',
        'worker',
        '--loglevel=info',
        '--pool=solo' if platform.system().lower() == 'windows' else '--pool=prefork'
    ]
    
    return subprocess.Popen(cmd, cwd=Path(__file__).parent)


def main():
    """Main entry point."""
    print("=" * 60)
    print("Audio Summarizer Backend - Windows Compatible")
    print("=" * 60)
    
    setup_environment()
    
    # Check if we should start both Flask and Celery
    start_mode = os.environ.get('START_MODE', 'both').lower()
    
    if start_mode in ['both', 'all']:
        logger.info("Starting both Flask app and Celery worker")
        
        # Start Celery worker in background
        worker_process = start_celery_worker()
        
        try:
            # Start Flask app (blocks)
            start_flask_app()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            worker_process.terminate()
            worker_process.wait()
    
    elif start_mode == 'flask':
        logger.info("Starting Flask app only")
        start_flask_app()
    
    elif start_mode == 'celery':
        logger.info("Starting Celery worker only")
        worker_process = start_celery_worker()
        try:
            worker_process.wait()
        except KeyboardInterrupt:
            logger.info("Shutting down Celery worker...")
            worker_process.terminate()
            worker_process.wait()
    
    else:
        logger.error(f"Unknown start mode: {start_mode}")
        print("Available modes: both, flask, celery")
        sys.exit(1)


if __name__ == "__main__":
    main()