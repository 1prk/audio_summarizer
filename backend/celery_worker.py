#!/usr/bin/env python
"""
Celery worker entry point for background task processing.
"""
import os
from app import create_app, init_celery


def make_celery_worker():
    """Create and configure Celery worker with Flask app context."""
    app = create_app()
    celery = init_celery(app)
    return celery


# Create Celery instance
celery = make_celery_worker()

if __name__ == '__main__':
    celery.start()