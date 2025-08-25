"""
Flask-RESTX API documentation setup with Swagger UI.
"""
from flask import Blueprint, render_template
from flask_restx import Api, Resource, Namespace
from .swagger_models import create_swagger_models

# Create the API documentation blueprint
api_bp = Blueprint('api_docs', __name__, template_folder='templates', static_folder='static')

# Initialize Flask-RESTX API
api = Api(
    api_bp,
    version='1.0.0',
    title='🎵 Audio Summarizer API',
    description="""
    **Personal Video Intelligence Platform API**
    
    Transform YouTube videos, podcasts, and Twitch streams into a searchable, visualized knowledge base with advanced AI-powered content analysis.
    
    ## Features
    - 🎬 **Multi-platform Processing**: YouTube, Twitch, Podcasts
    - 🎤 **Whisper Transcription**: High-quality speech-to-text
    - 🧠 **Content Intelligence**: Entity extraction, topic modeling, emotion analysis
    - 🔍 **Semantic Search**: Vector-based content discovery
    - 📊 **Real-time Progress**: WebSocket task monitoring
    - 🏥 **Health Monitoring**: Model readiness and system status
    
    ## Getting Started
    1. Check system health at `/api/health`
    2. Process videos via `/api/process/video`
    3. Monitor tasks at `/api/tasks/{task_id}`
    4. Explore intelligence at `/api/entities`, `/api/topics`, `/api/search/semantic`
    
    All models are pre-loaded at startup for optimal performance.
    """,
    doc='/swagger/',
    prefix='/api',
    contact='Audio Summarizer Team',
    contact_email='support@audiosummarizer.local',
    license='MIT',
    license_url='https://opensource.org/licenses/MIT',
    authorizations={
        'apikey': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-API-Key'
        }
    },
    security='apikey',
    tags=[
        {'name': 'Health', 'description': '🏥 System health and status endpoints - Monitor model readiness and service health'},
        {'name': 'Processing', 'description': '🎬 Video and content processing endpoints - Submit content for transcription and analysis'},
        {'name': 'Tasks', 'description': '⚡ Background task management - Monitor progress and manage running tasks'},
        {'name': 'Data', 'description': '📚 Content retrieval and data access - Access processed videos, transcripts, and metadata'},
        {'name': 'Intelligence', 'description': '🤖 Content intelligence and analysis - AI-powered entity extraction, topics, emotions, and search'}
    ]
)

# Create swagger models
models = create_swagger_models(api)

# Create namespaces
health_ns = Namespace('health', description='Health and system status operations', path='/api')
processing_ns = Namespace('processing', description='Video processing operations', path='/api')
tasks_ns = Namespace('tasks', description='Task management operations', path='/api')
data_ns = Namespace('data', description='Data retrieval operations', path='/api') 
intelligence_ns = Namespace('intelligence', description='Content intelligence operations', path='/api')

# Add namespaces to API
api.add_namespace(health_ns)
api.add_namespace(processing_ns)
api.add_namespace(tasks_ns)
api.add_namespace(data_ns)
api.add_namespace(intelligence_ns)

# Health Endpoints Documentation
@health_ns.route('/health')
class HealthCheck(Resource):
    @health_ns.doc(
        'health_check',
        description='Comprehensive health check for all system components including database, models, and services'
    )
    @health_ns.marshal_with(models['health'])
    @health_ns.response(200, 'System is healthy')
    @health_ns.response(503, 'System has issues', models['error'])
    def get(self):
        """Get system health status"""
        pass

@health_ns.route('/ping')
class Ping(Resource):
    @health_ns.doc(
        'ping',
        description='Simple ping endpoint to verify API connectivity'
    )
    @health_ns.marshal_with(models['ping'])
    def get(self):
        """Ping the API"""
        pass

# Processing Endpoints Documentation
@processing_ns.route('/process/video')
class ProcessVideo(Resource):
    @processing_ns.doc(
        'process_video',
        description='Queue a video for background processing with transcription and content intelligence analysis'
    )
    @processing_ns.expect(models['video_process_request'])
    @processing_ns.marshal_with(models['video_process_response'])
    @processing_ns.response(200, 'Video queued for processing')
    @processing_ns.response(400, 'Invalid request', models['error'])
    @processing_ns.response(503, 'Service unavailable', models['error'])
    def post(self):
        """Process a video with queue management"""
        pass

@processing_ns.route('/process/direct')
class ProcessDirect(Resource):
    @processing_ns.doc(
        'process_direct',
        description='Process a video directly without using the queue system for immediate results'
    )
    @processing_ns.expect(models['direct_process_request'])
    @processing_ns.marshal_with(models['video_process_response'])
    @processing_ns.response(200, 'Video processed directly')
    @processing_ns.response(400, 'Invalid request', models['error'])
    def post(self):
        """Process video directly without queue"""
        pass

@processing_ns.route('/process/batch')
class ProcessBatch(Resource):
    @processing_ns.doc(
        'process_batch',
        description='Process multiple videos in batch with efficient resource management'
    )
    @processing_ns.expect(models['batch_process_request'])
    @processing_ns.marshal_with(models['batch_process_response'])
    @processing_ns.response(200, 'Batch processing started')
    @processing_ns.response(400, 'Invalid request', models['error'])
    def post(self):
        """Process multiple videos in batch"""
        pass

# Task Management Documentation
@tasks_ns.route('/tasks/<string:task_id>')
class TaskStatus(Resource):
    @tasks_ns.doc(
        'get_task_status',
        description='Get detailed status information for a specific task including progress, errors, and results',
        params={'task_id': 'Unique task identifier'}
    )
    @tasks_ns.marshal_with(models['task_status_response'])
    @tasks_ns.response(200, 'Task status retrieved')
    @tasks_ns.response(404, 'Task not found', models['error'])
    def get(self, task_id):
        """Get task status and details"""
        pass

@tasks_ns.route('/tasks/<string:task_id>/cancel')
class CancelTask(Resource):
    @tasks_ns.doc(
        'cancel_task',
        description='Cancel a running or queued task',
        params={'task_id': 'Unique task identifier'}
    )
    @tasks_ns.marshal_with(models['cancel_task_response'])
    @tasks_ns.response(200, 'Task cancelled successfully')
    @tasks_ns.response(404, 'Task not found', models['error'])
    @tasks_ns.response(400, 'Task cannot be cancelled', models['error'])
    def post(self, task_id):
        """Cancel a task"""
        pass

@tasks_ns.route('/tasks')
class TasksList(Resource):
    @tasks_ns.doc(
        'get_tasks',
        description='Get list of tasks with filtering and pagination',
        params={
            'page': {'description': 'Page number', 'type': 'integer', 'default': 1},
            'per_page': {'description': 'Items per page', 'type': 'integer', 'default': 20},
            'status': {'description': 'Filter by task status', 'type': 'string', 'enum': ['queued', 'processing', 'completed', 'failed', 'cancelled']},
            'task_type': {'description': 'Filter by task type', 'type': 'string'}
        }
    )
    @tasks_ns.marshal_with(models['tasks_response'])
    def get(self):
        """Get list of tasks with filtering"""
        pass

# Data Endpoints Documentation
@data_ns.route('/videos')
class VideosList(Resource):
    @data_ns.doc(
        'get_videos',
        description='Get list of processed videos with filtering and pagination',
        params={
            'page': {'description': 'Page number', 'type': 'integer', 'default': 1},
            'per_page': {'description': 'Items per page', 'type': 'integer', 'default': 20},
            'status': {'description': 'Filter by processing status', 'type': 'string'}
        }
    )
    @data_ns.marshal_with(models['videos_response'])
    def get(self):
        """Get list of videos"""
        pass

@data_ns.route('/videos/<string:video_id>/transcripts')
class VideoTranscripts(Resource):
    @data_ns.doc(
        'get_video_transcripts',
        description='Get transcription segments for a specific video',
        params={'video_id': 'Unique video identifier'}
    )
    @data_ns.marshal_with(models['transcripts_response'])
    @data_ns.response(200, 'Transcripts retrieved')
    @data_ns.response(404, 'Video not found', models['error'])
    def get(self, video_id):
        """Get video transcripts"""
        pass

@data_ns.route('/channels')
class ChannelsList(Resource):
    @data_ns.doc(
        'get_channels',
        description='Get list of all discovered channels'
    )
    @data_ns.marshal_with(models['channels_response'])
    def get(self):
        """Get list of channels"""
        pass

# Content Intelligence Documentation
@intelligence_ns.route('/entities')
class EntitiesList(Resource):
    @intelligence_ns.doc(
        'get_entities',
        description='Get list of extracted entities with filtering options',
        params={
            'page': {'description': 'Page number', 'type': 'integer', 'default': 1},
            'per_page': {'description': 'Items per page', 'type': 'integer', 'default': 20},
            'type': {'description': 'Filter by entity type', 'type': 'string'},
            'min_confidence': {'description': 'Minimum confidence score', 'type': 'number'},
            'search': {'description': 'Search entity names', 'type': 'string'}
        }
    )
    @intelligence_ns.marshal_with(models['entities_response'])
    def get(self):
        """Get list of entities"""
        pass

@intelligence_ns.route('/videos/<string:video_id>/entities')
class VideoEntities(Resource):
    @intelligence_ns.doc(
        'get_video_entities',
        description='Get entities extracted from a specific video',
        params={
            'video_id': 'Unique video identifier',
            'min_confidence': {'description': 'Minimum confidence score', 'type': 'number'},
            'type': {'description': 'Filter by entity type', 'type': 'string'}
        }
    )
    @intelligence_ns.marshal_with(models['video_entities_response'])
    @intelligence_ns.response(200, 'Video entities retrieved')
    @intelligence_ns.response(404, 'Video not found', models['error'])
    def get(self, video_id):
        """Get entities from video"""
        pass

@intelligence_ns.route('/topics')
class TopicsList(Resource):
    @intelligence_ns.doc(
        'get_topics',
        description='Get list of discovered topics from content analysis',
        params={
            'search': {'description': 'Search topic labels', 'type': 'string'},
            'min_coherence': {'description': 'Minimum coherence score', 'type': 'number'}
        }
    )
    @intelligence_ns.marshal_with(models['topics_response'])
    def get(self):
        """Get list of topics"""
        pass

@intelligence_ns.route('/videos/<string:video_id>/topics')
class VideoTopics(Resource):
    @intelligence_ns.doc(
        'get_video_topics',
        description='Get topics associated with a specific video',
        params={
            'video_id': 'Unique video identifier',
            'min_probability': {'description': 'Minimum topic probability', 'type': 'number'}
        }
    )
    @intelligence_ns.marshal_with(models['video_topics_response'])
    @intelligence_ns.response(200, 'Video topics retrieved')
    @intelligence_ns.response(404, 'Video not found', models['error'])
    def get(self, video_id):
        """Get topics from video"""
        pass

@intelligence_ns.route('/search/semantic')
class SemanticSearch(Resource):
    @intelligence_ns.doc(
        'semantic_search',
        description='Perform semantic search across all content using vector embeddings'
    )
    @intelligence_ns.expect(models['semantic_search_request'])
    @intelligence_ns.marshal_list_with(models['search_result'])
    @intelligence_ns.response(200, 'Search results retrieved')
    @intelligence_ns.response(400, 'Invalid search query', models['error'])
    def post(self):
        """Perform semantic search"""
        pass

@intelligence_ns.route('/emotions')
class EmotionsList(Resource):
    @intelligence_ns.doc(
        'get_emotions',
        description='Get emotion analysis data across content',
        params={
            'video_id': {'description': 'Filter by video ID', 'type': 'string'}
        }
    )
    def get(self):
        """Get emotion analysis data"""
        pass

@intelligence_ns.route('/videos/<string:video_id>/emotions')
class VideoEmotions(Resource):
    @intelligence_ns.doc(
        'get_video_emotions',
        description='Get emotion analysis for a specific video including timeline data',
        params={'video_id': 'Unique video identifier'}
    )
    @intelligence_ns.marshal_with(models['video_emotions_response'])
    @intelligence_ns.response(200, 'Video emotions retrieved')
    @intelligence_ns.response(404, 'Video not found', models['error'])
    def get(self, video_id):
        """Get emotion analysis from video"""
        pass

@intelligence_ns.route('/embeddings')
class EmbeddingsList(Resource):
    @intelligence_ns.doc(
        'get_embeddings',
        description='Get vector embeddings information',
        params={
            'video_id': {'description': 'Filter by video ID', 'type': 'string'}
        }
    )
    @intelligence_ns.marshal_with(models['embeddings_response'])
    def get(self):
        """Get embeddings information"""
        pass

@intelligence_ns.route('/videos/<string:video_id>/process-intelligence')
class ProcessVideoIntelligence(Resource):
    @intelligence_ns.doc(
        'process_video_intelligence',
        description='Trigger content intelligence processing for a completed video. Requires all AI models to be loaded.',
        params={'video_id': 'Unique video identifier'}
    )
    @intelligence_ns.marshal_with(models['video_process_response'])
    @intelligence_ns.response(200, 'Intelligence processing started')
    @intelligence_ns.response(400, 'Video not ready for intelligence processing', models['error'])
    @intelligence_ns.response(404, 'Video not found', models['error'])
    @intelligence_ns.response(503, 'Required models not ready', models['error'])
    def post(self, video_id):
        """Process video intelligence"""
        pass

# Add routes for custom Swagger UI
@api_bp.route('/docs/')
def swagger_ui():
    """Serve custom Swagger UI"""
    return render_template('swagger-ui.html')

@api_bp.route('/docs/test')
def test_docs():
    """Test route to verify blueprint is working"""
    return {'message': 'API docs blueprint is working!', 'swagger_url': '/api/swagger/'}