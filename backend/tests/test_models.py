import pytest
import datetime
from app.models import db, Channel, Video, Transcript, ProcessingTask, Topic, Entity, Embedding, EmotionAnalysis


class TestChannelModel:
    """Test Channel model functionality."""
    
    def test_create_channel(self, app, sample_channel_data):
        """Test creating a channel."""
        with app.app_context():
            channel = Channel(**sample_channel_data)
            db.session.add(channel)
            db.session.commit()
            
            assert channel.id is not None
            assert channel.name == sample_channel_data['name']
            assert channel.platform == sample_channel_data['platform']
            assert channel.external_id == sample_channel_data['external_id']
            assert channel.is_active is True
            assert channel.created_at is not None
    
    def test_channel_videos_relationship(self, app, sample_channel_data, sample_video_data):
        """Test the relationship between channels and videos."""
        with app.app_context():
            channel = Channel(**sample_channel_data)
            db.session.add(channel)
            db.session.flush()  # To get channel.id without committing
            
            video = Video(
                title=sample_video_data['video_info']['title'],
                external_id=sample_video_data['video_info']['id'],
                url=sample_video_data['url'],
                channel_id=channel.id
            )
            db.session.add(video)
            db.session.commit()
            
            assert len(channel.videos) == 1
            assert channel.videos[0].title == sample_video_data['video_info']['title']


class TestVideoModel:
    """Test Video model functionality."""
    
    def test_create_video(self, app, sample_channel_data, sample_video_data):
        """Test creating a video."""
        with app.app_context():
            channel = Channel(**sample_channel_data)
            db.session.add(channel)
            db.session.flush()
            
            video = Video(
                title=sample_video_data['video_info']['title'],
                external_id=sample_video_data['video_info']['id'],
                url=sample_video_data['url'],
                description=sample_video_data['video_info']['description'],
                duration=sample_video_data['video_info']['duration'],
                view_count=sample_video_data['video_info']['view_count'],
                channel_id=channel.id
            )
            db.session.add(video)
            db.session.commit()
            
            assert video.id is not None
            assert video.title == sample_video_data['video_info']['title']
            assert video.external_id == sample_video_data['video_info']['id']
            assert video.processing_status == 'pending'
            assert video.created_at is not None
    
    def test_video_transcripts_relationship(self, app, sample_channel_data, sample_video_data):
        """Test the relationship between videos and transcripts."""
        with app.app_context():
            channel = Channel(**sample_channel_data)
            db.session.add(channel)
            db.session.flush()
            
            video = Video(
                title=sample_video_data['video_info']['title'],
                external_id=sample_video_data['video_info']['id'],
                url=sample_video_data['url'],
                channel_id=channel.id
            )
            db.session.add(video)
            db.session.flush()
            
            transcript = Transcript(
                text="This is a test transcript segment.",
                start_time=0.0,
                end_time=5.0,
                confidence=0.95,
                video_id=video.id
            )
            db.session.add(transcript)
            db.session.commit()
            
            assert len(video.transcripts) == 1
            assert video.transcripts[0].text == "This is a test transcript segment."


class TestTranscriptModel:
    """Test Transcript model functionality."""
    
    def test_create_transcript(self, app, sample_channel_data, sample_video_data):
        """Test creating a transcript."""
        with app.app_context():
            channel = Channel(**sample_channel_data)
            db.session.add(channel)
            db.session.flush()
            
            video = Video(
                title=sample_video_data['video_info']['title'],
                external_id=sample_video_data['video_info']['id'],
                url=sample_video_data['url'],
                channel_id=channel.id
            )
            db.session.add(video)
            db.session.flush()
            
            transcript = Transcript(
                text="This is a test transcript segment.",
                start_time=0.0,
                end_time=5.0,
                confidence=0.95,
                model_version="tiny",
                language_detected="en",
                video_id=video.id
            )
            db.session.add(transcript)
            db.session.commit()
            
            assert transcript.id is not None
            assert transcript.text == "This is a test transcript segment."
            assert transcript.start_time == 0.0
            assert transcript.end_time == 5.0
            assert transcript.confidence == 0.95
            assert transcript.model_version == "tiny"
            assert transcript.language_detected == "en"


class TestProcessingTaskModel:
    """Test ProcessingTask model functionality."""
    
    def test_create_processing_task(self, app):
        """Test creating a processing task."""
        with app.app_context():
            task = ProcessingTask(
                task_type='transcription',
                status='queued',
                input_data={'url': 'https://example.com/video'},
                max_retries=3
            )
            db.session.add(task)
            db.session.commit()
            
            assert task.id is not None
            assert task.task_type == 'transcription'
            assert task.status == 'queued'
            assert task.progress == 0.0
            assert task.retry_count == 0
            assert task.max_retries == 3
            assert task.created_at is not None
    
    def test_task_status_updates(self, app):
        """Test updating task status."""
        with app.app_context():
            task = ProcessingTask(
                task_type='transcription',
                status='queued'
            )
            db.session.add(task)
            db.session.commit()
            
            # Update to processing
            task.status = 'processing'
            task.started_at = datetime.datetime.utcnow()
            task.progress = 50.0
            db.session.commit()
            
            assert task.status == 'processing'
            assert task.started_at is not None
            assert task.progress == 50.0
            
            # Update to completed
            task.status = 'completed'
            task.completed_at = datetime.datetime.utcnow()
            task.progress = 100.0
            task.result_data = {'transcript_count': 42}
            db.session.commit()
            
            assert task.status == 'completed'
            assert task.completed_at is not None
            assert task.progress == 100.0
            assert task.result_data['transcript_count'] == 42


class TestTopicModel:
    """Test Topic model functionality."""
    
    def test_create_topic(self, app):
        """Test creating a topic."""
        with app.app_context():
            topic = Topic(
                name='Technology',
                description='Topics related to technology and software',
                keywords=['tech', 'software', 'programming'],
                coherence_score=0.85,
                document_count=100
            )
            db.session.add(topic)
            db.session.commit()
            
            assert topic.id is not None
            assert topic.name == 'Technology'
            assert topic.keywords == ['tech', 'software', 'programming']
            assert topic.coherence_score == 0.85
            assert topic.level == 0
    
    def test_hierarchical_topics(self, app):
        """Test hierarchical topic relationships."""
        with app.app_context():
            parent_topic = Topic(
                name='Technology',
                level=0
            )
            db.session.add(parent_topic)
            db.session.flush()
            
            child_topic = Topic(
                name='Machine Learning',
                parent_topic_id=parent_topic.id,
                level=1
            )
            db.session.add(child_topic)
            db.session.commit()
            
            assert len(parent_topic.children) == 1
            assert parent_topic.children[0].name == 'Machine Learning'
            assert child_topic.parent.name == 'Technology'


class TestEntityModel:
    """Test Entity model functionality."""
    
    def test_create_entity(self, app):
        """Test creating an entity."""
        with app.app_context():
            entity = Entity(
                name='Python',
                entity_type='TECH',
                canonical_name='Python Programming Language',
                description='A high-level programming language',
                confidence_score=0.95,
                mention_count=25
            )
            db.session.add(entity)
            db.session.commit()
            
            assert entity.id is not None
            assert entity.name == 'Python'
            assert entity.entity_type == 'TECH'
            assert entity.canonical_name == 'Python Programming Language'
            assert entity.confidence_score == 0.95
            assert entity.mention_count == 25


class TestEmbeddingModel:
    """Test Embedding model functionality."""
    
    def test_create_embedding(self, app, sample_channel_data, sample_video_data):
        """Test creating an embedding."""
        with app.app_context():
            channel = Channel(**sample_channel_data)
            db.session.add(channel)
            db.session.flush()
            
            video = Video(
                title=sample_video_data['video_info']['title'],
                external_id=sample_video_data['video_info']['id'],
                url=sample_video_data['url'],
                channel_id=channel.id
            )
            db.session.add(video)
            db.session.flush()
            
            embedding = Embedding(
                vector=[0.1, 0.2, 0.3, 0.4, 0.5],
                model_name='sentence-transformers/all-MiniLM-L6-v2',
                model_version='1.0',
                dimension=5,
                content_type='video',
                content_text='This is test content',
                video_id=video.id
            )
            db.session.add(embedding)
            db.session.commit()
            
            assert embedding.id is not None
            assert embedding.vector == [0.1, 0.2, 0.3, 0.4, 0.5]
            assert embedding.dimension == 5
            assert embedding.content_type == 'video'


class TestEmotionAnalysisModel:
    """Test EmotionAnalysis model functionality."""
    
    def test_create_emotion_analysis(self, app, sample_channel_data, sample_video_data):
        """Test creating emotion analysis."""
        with app.app_context():
            channel = Channel(**sample_channel_data)
            db.session.add(channel)
            db.session.flush()
            
            video = Video(
                title=sample_video_data['video_info']['title'],
                external_id=sample_video_data['video_info']['id'],
                url=sample_video_data['url'],
                channel_id=channel.id
            )
            db.session.add(video)
            db.session.flush()
            
            emotion_analysis = EmotionAnalysis(
                emotions={
                    'joy': 0.7,
                    'sadness': 0.1,
                    'anger': 0.2
                },
                dominant_emotion='joy',
                confidence_score=0.85,
                start_time=0.0,
                end_time=30.0,
                model_name='german-emotion-bert',
                model_version='1.0',
                video_id=video.id
            )
            db.session.add(emotion_analysis)
            db.session.commit()
            
            assert emotion_analysis.id is not None
            assert emotion_analysis.emotions['joy'] == 0.7
            assert emotion_analysis.dominant_emotion == 'joy'
            assert emotion_analysis.confidence_score == 0.85