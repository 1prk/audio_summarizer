"""
Swagger/OpenAPI models for API documentation using Flask-RESTX.
"""
from flask_restx import fields, Model

def create_swagger_models(api):
    """Create and register all Swagger models."""
    
    # Common Models
    health_model = api.model('Health', {
        'status': fields.String(required=True, description='Overall system health status'),
        'timestamp': fields.String(required=True, description='ISO timestamp of health check'),
        'version': fields.String(required=True, description='Application version'),
        'services': fields.Raw(required=True, description='Status of individual services')
    })
    
    ping_model = api.model('Ping', {
        'message': fields.String(required=True, description='Response message'),
        'timestamp': fields.String(required=True, description='ISO timestamp')
    })
    
    error_model = api.model('Error', {
        'error': fields.String(required=True, description='Error message'),
        'message': fields.String(description='Additional error details')
    })
    
    # Processing Models
    video_process_request = api.model('VideoProcessRequest', {
        'url': fields.String(required=True, description='Video URL to process', example='https://www.youtube.com/watch?v=dQw4w9WgXcQ'),
        'priority': fields.String(description='Processing priority', enum=['low', 'normal', 'high'], default='normal')
    })
    
    direct_process_request = api.model('DirectProcessRequest', {
        'url': fields.String(required=True, description='Video URL to process directly', example='https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    })
    
    batch_process_request = api.model('BatchProcessRequest', {
        'urls': fields.List(fields.String, required=True, description='List of video URLs to process', example=['https://www.youtube.com/watch?v=dQw4w9WgXcQ'])
    })
    
    video_process_response = api.model('VideoProcessResponse', {
        'task_id': fields.String(description='Task ID for tracking progress'),
        'video_id': fields.String(description='Video ID in database'),
        'status': fields.String(required=True, description='Processing status'),
        'message': fields.String(required=True, description='Status message'),
        'celery_task_id': fields.String(description='Celery task ID for background processing')
    })
    
    batch_task = api.model('BatchTask', {
        'task_id': fields.String(required=True, description='Task ID'),
        'url': fields.String(required=True, description='Video URL'),
        'celery_task_id': fields.String(required=True, description='Celery task ID')
    })
    
    batch_process_response = api.model('BatchProcessResponse', {
        'batch_id': fields.String(required=True, description='Batch processing ID'),
        'tasks': fields.List(fields.Nested(batch_task), required=True, description='Individual tasks in batch'),
        'message': fields.String(required=True, description='Batch processing status message')
    })
    
    # Task Models
    celery_info = api.model('CeleryInfo', {
        'task_id': fields.String(description='Celery task ID'),
        'state': fields.String(description='Celery task state'),
        'info': fields.Raw(description='Additional task information')
    })
    
    video_info = api.model('VideoInfo', {
        'id': fields.String(required=True, description='Video ID'),
        'title': fields.String(description='Video title'),
        'external_id': fields.String(description='External platform ID'),
        'processing_status': fields.String(description='Video processing status'),
        'platform': fields.String(description='Source platform')
    })
    
    task_status_response = api.model('TaskStatusResponse', {
        'task_id': fields.String(required=True, description='Task ID'),
        'status': fields.String(required=True, description='Task status'),
        'progress': fields.Float(required=True, description='Progress percentage (0-100)'),
        'task_type': fields.String(required=True, description='Type of task'),
        'created_at': fields.String(required=True, description='Task creation timestamp'),
        'started_at': fields.String(description='Task start timestamp'),
        'completed_at': fields.String(description='Task completion timestamp'),
        'error': fields.String(description='Error message if task failed'),
        'result': fields.Raw(description='Task result data'),
        'video': fields.Nested(video_info, description='Associated video information'),
        'celery': fields.Nested(celery_info, description='Celery task information'),
        'current_step': fields.String(description='Current processing step')
    })
    
    task = api.model('Task', {
        'id': fields.String(required=True, description='Task ID'),
        'task_type': fields.String(required=True, description='Type of task'),
        'status': fields.String(required=True, description='Task status'),
        'progress': fields.Float(required=True, description='Progress percentage'),
        'created_at': fields.String(required=True, description='Creation timestamp'),
        'started_at': fields.String(description='Start timestamp'),
        'completed_at': fields.String(description='Completion timestamp'),
        'input_data': fields.Raw(description='Task input data'),
        'video_id': fields.String(description='Associated video ID')
    })
    
    pagination = api.model('Pagination', {
        'page': fields.Integer(required=True, description='Current page number'),
        'per_page': fields.Integer(required=True, description='Items per page'),
        'total': fields.Integer(required=True, description='Total number of items'),
        'pages': fields.Integer(required=True, description='Total number of pages'),
        'has_next': fields.Boolean(required=True, description='Whether there is a next page'),
        'has_prev': fields.Boolean(required=True, description='Whether there is a previous page')
    })
    
    tasks_response = api.model('TasksResponse', {
        'tasks': fields.List(fields.Nested(task), required=True, description='List of tasks'),
        'pagination': fields.Nested(pagination, required=True, description='Pagination information')
    })
    
    cancel_task_response = api.model('CancelTaskResponse', {
        'task_id': fields.String(required=True, description='Cancelled task ID'),
        'status': fields.String(required=True, description='Cancellation status'),
        'message': fields.String(required=True, description='Cancellation message')
    })
    
    # Data Models
    channel = api.model('Channel', {
        'id': fields.String(required=True, description='Channel ID'),
        'name': fields.String(required=True, description='Channel name'),
        'platform': fields.String(required=True, description='Platform (youtube, twitch, etc.)'),
        'external_id': fields.String(required=True, description='External platform ID'),
        'url': fields.String(description='Channel URL'),
        'video_count': fields.Integer(description='Number of videos'),
        'created_at': fields.String(description='Channel creation timestamp')
    })
    
    channels_response = api.model('ChannelsResponse', {
        'channels': fields.List(fields.Nested(channel), required=True, description='List of channels')
    })
    
    video = api.model('Video', {
        'id': fields.String(required=True, description='Video ID'),
        'title': fields.String(required=True, description='Video title'),
        'external_id': fields.String(required=True, description='External platform ID'),
        'url': fields.String(required=True, description='Video URL'),
        'duration': fields.Float(description='Video duration in seconds'),
        'processing_status': fields.String(required=True, description='Processing status'),
        'created_at': fields.String(required=True, description='Creation timestamp'),
        'processed_at': fields.String(description='Processing completion timestamp'),
        'channel': fields.Nested(channel, description='Channel information')
    })
    
    videos_response = api.model('VideosResponse', {
        'videos': fields.List(fields.Nested(video), required=True, description='List of videos'),
        'pagination': fields.Nested(pagination, required=True, description='Pagination information')
    })
    
    transcript = api.model('Transcript', {
        'id': fields.String(required=True, description='Transcript segment ID'),
        'text': fields.String(required=True, description='Transcript text'),
        'start_time': fields.Float(required=True, description='Start time in seconds'),
        'end_time': fields.Float(required=True, description='End time in seconds'),
        'confidence': fields.Float(description='Transcription confidence score'),
        'speaker': fields.String(description='Speaker identification')
    })
    
    transcripts_response = api.model('TranscriptsResponse', {
        'video_id': fields.String(required=True, description='Video ID'),
        'video_title': fields.String(required=True, description='Video title'),
        'transcripts': fields.List(fields.Nested(transcript), required=True, description='Transcript segments')
    })
    
    # Content Intelligence Models
    entity_mention = api.model('EntityMention', {
        'id': fields.String(required=True, description='Mention ID'),
        'text': fields.String(required=True, description='Mentioned text'),
        'label': fields.String(required=True, description='Entity label/type'),
        'confidence': fields.Float(required=True, description='Confidence score'),
        'start': fields.Integer(required=True, description='Start character position'),
        'end': fields.Integer(required=True, description='End character position'),
        'videoId': fields.String(description='Associated video ID'),
        'timestamp': fields.Float(description='Timestamp in video')
    })
    
    entity = api.model('Entity', {
        'id': fields.String(required=True, description='Entity ID'),
        'name': fields.String(required=True, description='Entity name'),
        'entity_type': fields.String(required=True, description='Entity type'),
        'canonical_name': fields.String(description='Canonical form of entity name'),
        'description': fields.String(description='Entity description'),
        'confidence_score': fields.Float(required=True, description='Overall confidence score'),
        'mention_count': fields.Integer(required=True, description='Number of mentions'),
        'created_at': fields.String(required=True, description='Creation timestamp')
    })
    
    entities_response = api.model('EntitiesResponse', {
        'entities': fields.List(fields.Nested(entity), required=True, description='List of entities'),
        'pagination': fields.Nested(pagination, description='Pagination information')
    })
    
    video_entities_response = api.model('VideoEntitiesResponse', {
        'video_id': fields.String(required=True, description='Video ID'),
        'video_title': fields.String(required=True, description='Video title'),
        'entities': fields.List(fields.Nested(entity_mention), required=True, description='Entity mentions')
    })
    
    topic = api.model('Topic', {
        'id': fields.String(required=True, description='Topic ID'),
        'label': fields.String(required=True, description='Topic label'),
        'keywords': fields.List(fields.String, required=True, description='Topic keywords'),
        'coherence': fields.Float(required=True, description='Topic coherence score'),
        'documentCount': fields.Integer(required=True, description='Number of documents'),
        'evolution': fields.List(fields.Raw, description='Topic evolution over time'),
        'probability': fields.Float(description='Topic probability for document')
    })
    
    topics_response = api.model('TopicsResponse', {
        'topics': fields.List(fields.Nested(topic), required=True, description='List of topics')
    })
    
    video_topics_response = api.model('VideoTopicsResponse', {
        'video_id': fields.String(required=True, description='Video ID'),
        'video_title': fields.String(required=True, description='Video title'),
        'topics': fields.List(fields.Nested(topic), required=True, description='Video topics')
    })
    
    search_result = api.model('SearchResult', {
        'id': fields.String(required=True, description='Result ID'),
        'title': fields.String(required=True, description='Result title'),
        'similarity': fields.Float(required=True, description='Similarity score'),
        'snippet': fields.String(required=True, description='Text snippet'),
        'timestamp': fields.Float(description='Timestamp in content'),
        'channel': fields.String(description='Channel name'),
        'videoId': fields.String(description='Video ID'),
        'metadata': fields.Raw(description='Additional metadata')
    })
    
    semantic_search_request = api.model('SemanticSearchRequest', {
        'query': fields.String(required=True, description='Search query', example='machine learning algorithms'),
        'threshold': fields.Float(description='Similarity threshold', default=0.5),
        'limit': fields.Integer(description='Maximum number of results', default=10)
    })
    
    emotion_score = api.model('EmotionScore', {
        'emotion': fields.String(required=True, description='Emotion name'),
        'score': fields.Float(required=True, description='Emotion score'),
        'timestamp': fields.Float(description='Timestamp in content')
    })
    
    emotion_timeline = api.model('EmotionTimeline', {
        'timestamp': fields.Float(required=True, description='Timeline timestamp'),
        'emotions': fields.List(fields.Nested(emotion_score), required=True, description='Emotions at timestamp'),
        'dominantEmotion': fields.String(required=True, description='Dominant emotion')
    })
    
    video_emotions_response = api.model('VideoEmotionsResponse', {
        'video_id': fields.String(required=True, description='Video ID'),
        'video_title': fields.String(required=True, description='Video title'),
        'emotions': fields.List(fields.Nested(emotion_score), required=True, description='Overall emotions'),
        'timeline': fields.List(fields.Nested(emotion_timeline), required=True, description='Emotion timeline')
    })
    
    embedding = api.model('Embedding', {
        'id': fields.String(required=True, description='Embedding ID'),
        'model_name': fields.String(required=True, description='Model used for embedding'),
        'model_version': fields.String(required=True, description='Model version'),
        'dimension': fields.Integer(required=True, description='Embedding dimension'),
        'content_type': fields.String(required=True, description='Type of content embedded'),
        'video_id': fields.String(required=True, description='Associated video ID'),
        'created_at': fields.String(required=True, description='Creation timestamp')
    })
    
    embeddings_response = api.model('EmbeddingsResponse', {
        'embeddings': fields.List(fields.Nested(embedding), required=True, description='List of embeddings')
    })
    
    return {
        'health': health_model,
        'ping': ping_model,
        'error': error_model,
        'video_process_request': video_process_request,
        'direct_process_request': direct_process_request,
        'batch_process_request': batch_process_request,
        'video_process_response': video_process_response,
        'batch_process_response': batch_process_response,
        'task_status_response': task_status_response,
        'tasks_response': tasks_response,
        'cancel_task_response': cancel_task_response,
        'channels_response': channels_response,
        'videos_response': videos_response,
        'transcripts_response': transcripts_response,
        'entities_response': entities_response,
        'video_entities_response': video_entities_response,
        'topics_response': topics_response,
        'video_topics_response': video_topics_response,
        'search_result': search_result,
        'semantic_search_request': semantic_search_request,
        'video_emotions_response': video_emotions_response,
        'embeddings_response': embeddings_response
    }