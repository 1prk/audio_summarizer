import pytest
import os
from app.config import Config, DevelopmentConfig, ProductionConfig, TestingConfig


class TestConfiguration:
    """Test configuration classes."""
    
    def test_base_config(self):
        """Test base configuration."""
        config = Config()
        
        # Test default values
        assert config.SQLALCHEMY_TRACK_MODIFICATIONS is False
        assert config.WHISPER_MODEL == 'tiny'
        assert config.WHISPER_DEVICE == 'cpu'
        assert config.LOG_LEVEL == 'INFO'
        assert config.MAX_CONTENT_LENGTH == 16777216
        assert config.UPLOAD_TIMEOUT == 3600
    
    def test_development_config(self):
        """Test development configuration."""
        config = DevelopmentConfig()
        
        assert config.DEBUG is True
        assert config.FLASK_ENV == 'development'
    
    def test_production_config(self):
        """Test production configuration."""
        config = ProductionConfig()
        
        assert config.DEBUG is False
        assert config.FLASK_ENV == 'production'
    
    def test_testing_config(self):
        """Test testing configuration."""
        config = TestingConfig()
        
        assert config.TESTING is True
        assert config.SQLALCHEMY_DATABASE_URI == 'sqlite:///:memory:'
        assert config.WTF_CSRF_ENABLED is False
    
    def test_environment_variable_override(self, monkeypatch):
        """Test that environment variables override defaults."""
        # Set environment variables
        monkeypatch.setenv('SECRET_KEY', 'test-secret-key')
        monkeypatch.setenv('WHISPER_MODEL', 'base')
        monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
        monkeypatch.setenv('MAX_CONTENT_LENGTH', '33554432')
        
        # Reload dotenv to pick up new env vars
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        # Create new config instance to pick up env vars
        config = Config()
        
        assert config.SECRET_KEY == 'test-secret-key'
        assert config.WHISPER_MODEL == 'base'
        assert config.LOG_LEVEL == 'DEBUG'
        assert config.MAX_CONTENT_LENGTH == 33554432
    
    def test_database_url_postgres_conversion(self, monkeypatch):
        """Test that postgres:// URLs are converted to postgresql://."""
        monkeypatch.setenv('DATABASE_URL', 'postgres://user:pass@localhost:5432/db')
        
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        config = Config()
        
        assert config.SQLALCHEMY_DATABASE_URI.startswith('postgresql://')
        assert 'user:pass@localhost:5432/db' in config.SQLALCHEMY_DATABASE_URI
    
    def test_database_url_postgresql_unchanged(self, monkeypatch):
        """Test that postgresql:// URLs remain unchanged."""
        url = 'postgresql://user:pass@localhost:5432/db'
        monkeypatch.setenv('DATABASE_URL', url)
        
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        config = Config()
        
        assert config.SQLALCHEMY_DATABASE_URI == url
    
    def test_missing_environment_variables(self):
        """Test behavior when environment variables are missing."""
        config = Config()
        
        # Should fall back to defaults or None
        assert config.OPENAI_API_KEY is None  # No default for this
        assert config.REDIS_URL == 'redis://localhost:6379/0'  # Has default