"""
Celery application configuration for background task processing.
"""
from celery import Celery
from app.config import config
import os
import logging

logger = logging.getLogger(__name__)


def make_celery(app_name=__name__):
    """Create and configure Celery instance."""
    config_name = os.environ.get('FLASK_ENV', 'default')
    app_config = config[config_name]
    
    # Handle Windows fallback - use SQLite instead of memory
    if getattr(app_config, 'USE_REDIS_FALLBACK', False):
        logger.info("Using SQLite file-based broker for Windows")
        
        # Create broker directory
        broker_dir = os.path.join(os.getcwd(), 'celery_broker')
        os.makedirs(broker_dir, exist_ok=True)
        
        # Use SQLite as broker and backend
        broker_db = os.path.join(broker_dir, 'broker.db')
        result_db = os.path.join(broker_dir, 'results.db')
        
        celery = Celery(
            app_name,
            broker=f'sqla+sqlite:///{broker_db}',
            backend=f'db+sqlite:///{result_db}',
            include=['app.tasks']
        )
        
        logger.info(f"Using SQLite broker: {broker_db}")
        logger.info(f"Using SQLite results: {result_db}")
    else:
        # Standard Redis configuration
        celery = Celery(
            app_name,
            broker=app_config.CELERY_BROKER_URL,
            backend=app_config.CELERY_RESULT_BACKEND,
            include=['app.tasks']
        )
    
    # Update configuration
    celery.conf.update(
        # Task routing - commented out to use default queue for now
        # task_routes={
        #     'app.tasks.transcribe_video': {'queue': 'transcription'},
        #     'app.tasks.extract_metadata': {'queue': 'metadata'},
        #     'app.tasks.cleanup_files': {'queue': 'cleanup'},
        # },
        
        # Task priority levels
        task_default_queue='default',
        task_default_exchange='default',
        task_default_exchange_type='direct',
        task_default_routing_key='default',
        
        # Worker configuration
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        
        # Result backend settings
        result_expires=3600,  # 1 hour
        result_persistent=True,
        
        # Task retry settings
        task_annotations={
            '*': {
                'rate_limit': '10/s',
                'time_limit': 600,  # 10 minutes
                'soft_time_limit': 540,  # 9 minutes
            },
            'app.tasks.transcribe_video': {
                'rate_limit': '5/m',  # 5 per minute
                'time_limit': 1800,  # 30 minutes
                'soft_time_limit': 1620,  # 27 minutes
                'max_retries': 3,
                'default_retry_delay': 60,
            },
            'app.tasks.cleanup_files': {
                'rate_limit': '30/m',
                'time_limit': 60,
                'max_retries': 1,
            }
        },
        
        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,
        
        # Serialization
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        
        # Beat scheduler (for periodic tasks)
        beat_schedule={
            'cleanup-expired-files': {
                'task': 'app.tasks.cleanup_expired_files',
                'schedule': 3600.0,  # Every hour
            },
            'health-check': {
                'task': 'app.tasks.system_health_check',
                'schedule': 300.0,  # Every 5 minutes
            },
        },
    )
    
    return celery


# Create the Celery instance
celery = make_celery()