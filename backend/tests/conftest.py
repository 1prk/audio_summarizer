import pytest
import tempfile
import os
from app import create_app
from app.models import db


@pytest.fixture
def app():
    """Create application for the tests."""
    # Create a temporary file for the test database
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app('testing')
    app.config['DATABASE_URL'] = f'sqlite:///{db_path}'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture
def sample_video_data():
    """Sample video data for testing."""
    return {
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'video_info': {
            'id': 'dQw4w9WgXcQ',
            'title': 'Test Video',
            'description': 'A test video description',
            'duration': 213,
            'upload_date': '20091025',
            'uploader': 'Test Channel',
            'uploader_id': 'UCTest123',
            'view_count': 1000000,
            'like_count': 50000,
            'thumbnail': 'https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg',
            'channel_url': 'https://www.youtube.com/channel/UCTest123'
        }
    }


@pytest.fixture
def sample_channel_data():
    """Sample channel data for testing."""
    return {
        'name': 'Test Channel',
        'platform': 'youtube',
        'external_id': 'UCTest123',
        'url': 'https://www.youtube.com/channel/UCTest123',
        'description': 'A test channel'
    }