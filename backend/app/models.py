from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Channel(db.Model):
    """Model for content channels (YouTube channels, podcast feeds, etc.)"""
    __tablename__ = 'channels'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # youtube, podcast, twitch
    external_id = db.Column(db.String(255), unique=True, nullable=False)  # Channel ID on platform
    url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    avatar_url = db.Column(db.String(500))
    subscriber_count = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    videos = db.relationship('Video', backref='channel', lazy=True, cascade='all, delete-orphan')


class Video(db.Model):
    """Model for individual videos/episodes"""
    __tablename__ = 'videos'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(500), nullable=False)
    external_id = db.Column(db.String(255), nullable=False)  # Video ID on platform
    url = db.Column(db.String(500), nullable=False)
    platform = db.Column(db.String(50), nullable=False, default='youtube')  # youtube, podcast, twitch
    description = db.Column(db.Text)
    thumbnail_url = db.Column(db.String(500))
    duration = db.Column(db.Integer)  # Duration in seconds
    published_at = db.Column(db.DateTime)
    view_count = db.Column(db.BigInteger)
    like_count = db.Column(db.Integer)
    comment_count = db.Column(db.Integer)
    language = db.Column(db.String(10))
    
    # Processing status
    processing_status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    audio_file_path = db.Column(db.String(500))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    
    # Foreign Keys
    channel_id = db.Column(db.String(36), db.ForeignKey('channels.id'), nullable=False)
    
    # Relationships
    transcripts = db.relationship('Transcript', backref='video', lazy=True, cascade='all, delete-orphan')
    embeddings = db.relationship('Embedding', backref='video', lazy=True, cascade='all, delete-orphan')
    emotions = db.relationship('EmotionAnalysis', backref='video', lazy=True, cascade='all, delete-orphan')
    entity_mentions = db.relationship('EntityMention', backref='video', lazy=True, cascade='all, delete-orphan')
    topic_assignments = db.relationship('TopicAssignment', backref='video', lazy=True, cascade='all, delete-orphan')


class Transcript(db.Model):
    """Model for video transcripts"""
    __tablename__ = 'transcripts'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    text = db.Column(db.Text, nullable=False)
    start_time = db.Column(db.Float)  # Start time in seconds
    end_time = db.Column(db.Float)  # End time in seconds
    confidence = db.Column(db.Float)  # Transcription confidence score
    speaker = db.Column(db.String(255))  # Speaker identification if available
    
    # Processing metadata
    model_version = db.Column(db.String(50))
    language_detected = db.Column(db.String(10))
    processing_metadata = db.Column(db.JSON)  # Additional metadata including LLM cleaning info
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    video_id = db.Column(db.String(36), db.ForeignKey('videos.id'), nullable=False)


class Topic(db.Model):
    """Model for discovered topics from content"""
    __tablename__ = 'topics'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    keywords = db.Column(db.JSON)  # List of associated keywords
    coherence_score = db.Column(db.Float)  # Topic coherence metric
    document_count = db.Column(db.Integer, default=0)  # Number of documents with this topic
    
    # Hierarchical topics
    parent_topic_id = db.Column(db.String(36), db.ForeignKey('topics.id'))
    level = db.Column(db.Integer, default=0)  # Hierarchy level
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent = db.relationship('Topic', remote_side=[id], backref='children')
    assignments = db.relationship('TopicAssignment', backref='topic', lazy=True, cascade='all, delete-orphan')


class Entity(db.Model):
    """Model for extracted entities"""
    __tablename__ = 'entities'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    entity_type = db.Column(db.String(100), nullable=False)  # PERSON, ORG, TECH, etc.
    canonical_name = db.Column(db.String(255))  # Normalized/canonical form
    description = db.Column(db.Text)
    external_id = db.Column(db.String(255))  # ID from external source (Wikipedia, etc.)
    confidence_score = db.Column(db.Float)
    mention_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    mentions = db.relationship('EntityMention', backref='entity', lazy=True, cascade='all, delete-orphan')


class EntityMention(db.Model):
    """Model for entity mentions in specific videos/transcripts"""
    __tablename__ = 'entity_mentions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    text = db.Column(db.String(500), nullable=False)  # Original mention text
    start_char = db.Column(db.Integer)  # Character position in text
    end_char = db.Column(db.Integer)
    confidence = db.Column(db.Float, nullable=False)
    context = db.Column(db.Text)  # Surrounding text context
    
    # Time reference for video mentions
    timestamp = db.Column(db.Float)  # Time in video when mentioned
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    entity_id = db.Column(db.String(36), db.ForeignKey('entities.id'), nullable=False)
    video_id = db.Column(db.String(36), db.ForeignKey('videos.id'), nullable=False)
    transcript_id = db.Column(db.String(36), db.ForeignKey('transcripts.id'))


class TopicAssignment(db.Model):
    """Model for topic assignments to videos"""
    __tablename__ = 'topic_assignments'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    probability = db.Column(db.Float, nullable=False)  # Topic assignment probability
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    topic_id = db.Column(db.String(36), db.ForeignKey('topics.id'), nullable=False)
    video_id = db.Column(db.String(36), db.ForeignKey('videos.id'), nullable=False)


class Embedding(db.Model):
    """Model for vector embeddings"""
    __tablename__ = 'embeddings'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vector = db.Column(db.JSON, nullable=False)  # Vector as JSON array
    model_name = db.Column(db.String(100), nullable=False)
    model_version = db.Column(db.String(50))
    dimension = db.Column(db.Integer, nullable=False)
    
    # Content reference
    content_type = db.Column(db.String(50), nullable=False)  # video, transcript_segment, topic
    content_text = db.Column(db.Text)  # Original text that was embedded
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    video_id = db.Column(db.String(36), db.ForeignKey('videos.id'), nullable=False)
    transcript_id = db.Column(db.String(36), db.ForeignKey('transcripts.id'))


class EmotionAnalysis(db.Model):
    """Model for emotion analysis results"""
    __tablename__ = 'emotion_analysis'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    emotions = db.Column(db.JSON, nullable=False)  # Dict of emotion: score pairs
    dominant_emotion = db.Column(db.String(50))
    confidence_score = db.Column(db.Float)
    
    # Time segment for the analysis
    start_time = db.Column(db.Float)
    end_time = db.Column(db.Float)
    
    # Model information
    model_name = db.Column(db.String(100), nullable=False)
    model_version = db.Column(db.String(50))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    video_id = db.Column(db.String(36), db.ForeignKey('videos.id'), nullable=False)


class ProcessingTask(db.Model):
    """Model for tracking background processing tasks"""
    __tablename__ = 'processing_tasks'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type = db.Column(db.String(100), nullable=False)  # transcription, embedding, emotion_analysis
    status = db.Column(db.String(50), default='queued')  # queued, processing, completed, failed
    progress = db.Column(db.Float, default=0.0)  # Progress percentage 0-100
    
    # Task data
    input_data = db.Column(db.JSON)  # Task input parameters
    result_data = db.Column(db.JSON)  # Task results
    error_message = db.Column(db.Text)  # Error details if failed
    
    # Retry logic
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Foreign Keys
    video_id = db.Column(db.String(36), db.ForeignKey('videos.id'))