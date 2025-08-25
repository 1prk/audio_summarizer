import pytest
import os
import tempfile
from app import create_app
from app.models import db


class TestAppFactory:
    """Test Flask application factory."""
    
    def test_create_app_default_config(self):
        """Test creating app with default configuration."""
        app = create_app()
        
        assert app is not None
        assert app.config['TESTING'] is False
    
    def test_create_app_testing_config(self):
        """Test creating app with testing configuration."""
        app = create_app('testing')
        
        assert app is not None
        assert app.config['TESTING'] is True
        assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'
    
    def test_create_app_development_config(self):
        """Test creating app with development configuration."""
        app = create_app('development')
        
        assert app is not None
        assert app.config['DEBUG'] is True
        assert app.config['FLASK_ENV'] == 'development'
    
    def test_create_app_production_config(self):
        """Test creating app with production configuration."""
        app = create_app('production')
        
        assert app is not None
        assert app.config['DEBUG'] is False
        assert app.config['FLASK_ENV'] == 'production'
    
    def test_app_has_required_extensions(self):
        """Test that app has all required extensions initialized."""
        app = create_app('testing')
        
        with app.app_context():
            # Test database extension
            assert hasattr(app, 'extensions')
            assert 'sqlalchemy' in app.extensions
            
            # Test that tables are created
            db.create_all()
            # Should not raise an error
    
    def test_app_has_blueprints_registered(self):
        """Test that required blueprints are registered."""
        app = create_app('testing')
        
        # Check that the API blueprint is registered
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        assert 'api' in blueprint_names
    
    def test_app_cors_enabled(self):
        """Test that CORS is enabled."""
        app = create_app('testing')
        
        # Check that CORS extension is loaded
        assert 'cors' in app.extensions
    
    def test_logging_setup_production(self, monkeypatch):
        """Test logging setup in production mode."""
        # Create a temporary directory for logs
        with tempfile.TemporaryDirectory() as temp_dir:
            original_dir = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                app = create_app('production')
                
                # In production mode, logging should be configured
                assert app.logger.level != 0  # Should have a logging level set
                
            finally:
                os.chdir(original_dir)
    
    def test_database_tables_created(self):
        """Test that database tables are created on app startup."""
        app = create_app('testing')
        
        with app.app_context():
            # Tables should be created automatically
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            expected_tables = [
                'channels', 'videos', 'transcripts', 'topics', 
                'entities', 'embeddings', 'emotion_analysis', 
                'processing_tasks'
            ]
            
            for table in expected_tables:
                assert table in tables, f"Table {table} not found in database"