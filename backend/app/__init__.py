from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_socketio import SocketIO
import logging
import os
from .config import config
from .models import db

migrate = Migrate()
socketio = SocketIO()

def create_app(config_name=None):
    """Application factory pattern for Flask app creation."""
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    
    # Configure logging
    setup_logging(app)
    
    # Register blueprints
    from .routes import api
    app.register_blueprint(api, url_prefix='/api')
    
    # Register API documentation
    try:
        from .api_docs import api_bp
        app.register_blueprint(api_bp)
        app.logger.info("API documentation blueprint registered successfully")
    except Exception as e:
        app.logger.error(f"Failed to register API docs blueprint: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
    
    # Add a simple route to check available URLs
    @app.route('/debug-routes')
    def debug_routes():
        import urllib
        output = []
        for rule in app.url_map.iter_rules():
            options = {}
            for arg in rule.arguments:
                options[arg] = "[{0}]".format(arg)
            
            methods = ','.join(rule.methods)
            url = rule.rule
            if rule.endpoint:
                output.append({
                    'endpoint': rule.endpoint,
                    'methods': methods,
                    'url': url
                })
        
        return {'available_routes': sorted(output, key=lambda x: x['url'])}
    
    # Add a simple docs test route
    @app.route('/docs-simple')
    def docs_simple():
        return '''
        <html>
        <head><title>Simple Docs Test</title></head>
        <body>
            <h1>Docs Test Working!</h1>
            <p>If you see this, Flask is working but there might be a blueprint issue.</p>
            <a href="/debug-routes">Check Available Routes</a>
        </body>
        </html>
        '''
    
    # Register WebSocket events
    register_socketio_events(app)
    
    # Create tables if they don't exist (for development)
    with app.app_context():
        db.create_all()
    
    return app

def register_socketio_events(app):
    """Register WebSocket events for real-time updates."""
    @socketio.on('connect')
    def handle_connect():
        print('Client connected')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected')
    
    @socketio.on('subscribe_task')
    def handle_subscribe_task(data):
        """Subscribe to task updates."""
        task_id = data.get('task_id')
        if task_id:
            from flask_socketio import join_room
            join_room(f'task_{task_id}')
            print(f'Client subscribed to task {task_id}')

def init_celery(app):
    """Initialize Celery with Flask app context."""
    from .celery_app import celery
    
    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context."""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

def setup_logging(app):
    """Configure application logging."""
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = logging.FileHandler('logs/audio_summarizer.log')
        file_handler.setFormatter(logging.Formatter(
            app.config['LOG_FORMAT']
        ))
        file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.info('Audio Summarizer startup')