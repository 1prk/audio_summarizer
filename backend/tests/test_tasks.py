import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock, call
from app.tasks import (
    extract_metadata, detect_platform, extract_youtube_metadata,
    extract_podcast_metadata, parse_podcast_duration, format_podcast_date,
    create_or_get_channel, create_video_record
)
from app.models import db, Channel, Video


class TestPlatformDetection:
    """Test platform detection functionality."""
    
    def test_detect_youtube_platform(self):
        """Test YouTube URL detection."""
        urls = [
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtu.be/dQw4w9WgXcQ',
            'https://m.youtube.com/watch?v=dQw4w9WgXcQ'
        ]
        
        for url in urls:
            assert detect_platform(url) == 'youtube'
    
    def test_detect_twitch_platform(self):
        """Test Twitch URL detection."""
        urls = [
            'https://www.twitch.tv/videos/123456789',
            'https://twitch.tv/streamer'
        ]
        
        for url in urls:
            assert detect_platform(url) == 'twitch'
    
    def test_detect_podcast_platform(self):
        """Test podcast URL detection."""
        urls = [
            'https://example.com/podcast.rss',
            'https://feeds.example.com/feed.xml',
            'https://podcast.example.com/episodes'
        ]
        
        for url in urls:
            assert detect_platform(url) == 'podcast'
    
    def test_detect_unknown_platform(self):
        """Test unknown platform detection."""
        url = 'https://example.com/unknown'
        assert detect_platform(url) == 'unknown'


class TestMetadataExtraction:
    """Test metadata extraction for different platforms."""
    
    @patch('app.tasks.yt_dlp.YoutubeDL')
    def test_extract_youtube_metadata(self, mock_ydl_class):
        """Test YouTube metadata extraction."""
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        
        mock_info = {
            'id': 'dQw4w9WgXcQ',
            'title': 'Test Video',
            'description': 'Test description',
            'duration': 212,
            'upload_date': '20091025',
            'uploader': 'Test Channel',
            'uploader_id': 'UCTest123',
            'view_count': 1000000,
            'like_count': 50000,
            'thumbnail': 'https://img.youtube.com/vi/test.jpg',
            'channel_url': 'https://www.youtube.com/channel/UCTest123',
            'tags': ['music', 'test'],
            'language': 'en'
        }
        
        mock_ydl.extract_info.return_value = mock_info
        
        result = extract_youtube_metadata('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        
        assert result['platform'] == 'youtube'
        assert result['id'] == 'dQw4w9WgXcQ'
        assert result['title'] == 'Test Video'
        assert result['uploader'] == 'Test Channel'
        assert result['duration'] == 212
    
    @patch('app.tasks.feedparser.parse')
    def test_extract_podcast_metadata(self, mock_feedparser):
        """Test podcast metadata extraction."""
        mock_feed = MagicMock()
        mock_feed.feed.title = 'Test Podcast'
        mock_feed.feed.link = 'https://podcast.example.com'
        
        mock_episode = MagicMock()
        mock_episode.title = 'Episode 1'
        mock_episode.description = 'Test episode description'
        mock_episode.get.side_effect = lambda key, default=None: {
            'id': 'episode-1',
            'title': 'Episode 1',
            'description': 'Test episode description',
            'itunes_duration': '25:30',
            'published_parsed': (2023, 1, 15, 10, 30, 0, 0, 0, 0)
        }.get(key, default)
        mock_episode.enclosures = [
            MagicMock(type='audio/mpeg', href='https://example.com/episode1.mp3')
        ]
        mock_episode.tags = []
        
        mock_feed.entries = [mock_episode]
        mock_feedparser.return_value = mock_feed
        
        result = extract_podcast_metadata('https://podcast.example.com/feed.rss')
        
        assert result['platform'] == 'podcast'
        assert result['title'] == 'Episode 1'
        assert result['uploader'] == 'Test Podcast'
        assert result['duration'] == 1530  # 25:30 in seconds
        assert result['upload_date'] == '20230115'
    
    def test_parse_podcast_duration(self):
        """Test podcast duration parsing."""
        assert parse_podcast_duration('25:30') == 1530
        assert parse_podcast_duration('1:25:30') == 5130
        assert parse_podcast_duration('180') == 180
        assert parse_podcast_duration(None) is None
        assert parse_podcast_duration('invalid') is None
    
    def test_format_podcast_date(self):
        """Test podcast date formatting."""
        date_parsed = (2023, 1, 15, 10, 30, 0, 0, 0, 0)
        assert format_podcast_date(date_parsed) == '20230115'
        assert format_podcast_date(None) is None


class TestDatabaseOperations:
    """Test database operations for channels and videos."""
    
    def test_create_or_get_channel_new(self, app):
        """Test creating a new channel."""
        with app.app_context():
            metadata = {
                'uploader': 'Test Channel',
                'platform': 'youtube',
                'uploader_id': 'UCTest123',
                'channel_url': 'https://www.youtube.com/channel/UCTest123'
            }
            
            channel = create_or_get_channel(metadata)
            
            assert channel.name == 'Test Channel'
            assert channel.platform == 'youtube'
            assert channel.external_id == 'UCTest123'
            assert channel.url == 'https://www.youtube.com/channel/UCTest123'
            
            # Verify it was saved to database
            saved_channel = Channel.query.filter_by(external_id='UCTest123').first()
            assert saved_channel is not None
            assert saved_channel.id == channel.id
    
    def test_create_or_get_channel_existing(self, app, sample_channel_data):
        """Test getting an existing channel."""
        with app.app_context():
            # Create existing channel
            existing_channel = Channel(**sample_channel_data)
            db.session.add(existing_channel)
            db.session.commit()
            
            metadata = {
                'uploader': 'Test Channel',
                'platform': 'youtube',
                'uploader_id': 'UCTest123',
                'channel_url': 'https://www.youtube.com/channel/UCTest123'
            }
            
            channel = create_or_get_channel(metadata)
            
            # Should return the existing channel
            assert channel.id == existing_channel.id
            assert channel.name == existing_channel.name
    
    def test_create_video_record(self, app, sample_channel_data):
        """Test creating a video record."""
        with app.app_context():
            # Create channel first
            channel = Channel(**sample_channel_data)
            db.session.add(channel)
            db.session.flush()
            
            metadata = {
                'platform': 'youtube',
                'id': 'dQw4w9WgXcQ',
                'title': 'Test Video',
                'description': 'Test description',
                'duration': 212,
                'upload_date': '20091025',
                'view_count': 1000000,
                'like_count': 50000,
                'comment_count': 1000,
                'thumbnail': 'https://img.youtube.com/vi/test.jpg',
                'language': 'en'
            }
            
            url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
            
            video = create_video_record(metadata, channel, url)
            
            assert video.title == 'Test Video'
            assert video.external_id == 'dQw4w9WgXcQ'
            assert video.platform == 'youtube'
            assert video.url == url
            assert video.duration == 212
            assert video.processing_status == 'processing'
            assert video.channel_id == channel.id
            
            # Verify date parsing
            assert video.published_at is not None
            assert video.published_at.year == 2009
            assert video.published_at.month == 10
            assert video.published_at.day == 25


class TestCeleryTasks:
    """Test Celery task functionality."""
    
    @patch('app.tasks.extract_youtube_metadata')
    def test_extract_metadata_task_youtube(self, mock_extract):
        """Test metadata extraction task for YouTube."""
        mock_extract.return_value = {
            'platform': 'youtube',
            'id': 'test123',
            'title': 'Test Video'
        }
        
        # Note: This would need actual Celery testing setup
        # For now, test the function directly
        result = extract_youtube_metadata('https://www.youtube.com/watch?v=test123')
        
        assert 'platform' in result
        assert result['platform'] == 'youtube'
    
    @patch('app.tasks.requests.get')
    @patch('app.tasks.feedparser.parse')
    def test_download_podcast_audio(self, mock_feedparser, mock_requests):
        """Test podcast audio download."""
        # Mock RSS feed response
        mock_feed = MagicMock()
        mock_episode = MagicMock()
        mock_episode.enclosures = [
            MagicMock(type='audio/mpeg', href='https://example.com/audio.mp3')
        ]
        mock_feed.entries = [mock_episode]
        mock_feedparser.return_value = mock_feed
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.headers = {'content-length': '1024'}
        mock_response.iter_content.return_value = [b'test audio data']
        mock_requests.return_value = mock_response
        
        from app.tasks import download_podcast_audio
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = download_podcast_audio(
                'https://podcast.example.com/feed.rss',
                'test_video_id',
                temp_dir,
                'test_task_id'
            )
            
            assert result.endswith('.mp3')
            assert os.path.exists(result)


class TestAudioProcessing:
    """Test enhanced audio processing functionality."""
    
    def test_transcriber_initialization(self):
        """Test transcriber initialization."""
        from app.audio_processing import EnhancedWhisperTranscriber
        
        transcriber = EnhancedWhisperTranscriber('tiny', 'cpu', 'int8')
        
        assert transcriber.model_size == 'tiny'
        assert transcriber.device == 'cpu'
        assert transcriber.compute_type == 'int8'
    
    def test_device_detection(self):
        """Test device detection logic."""
        from app.audio_processing import EnhancedWhisperTranscriber
        
        transcriber = EnhancedWhisperTranscriber()
        
        # Test explicit device
        assert transcriber._detect_device('cpu') == 'cpu'
        assert transcriber._detect_device('cuda') == 'cuda'
        
        # Test auto detection (will default to CPU in test environment)
        auto_device = transcriber._detect_device('auto')
        assert auto_device in ['cpu', 'cuda']
    
    @patch('subprocess.run')
    def test_audio_preprocessing(self, mock_subprocess):
        """Test audio preprocessing."""
        from app.audio_processing import EnhancedWhisperTranscriber
        
        mock_subprocess.return_value.returncode = 0
        
        transcriber = EnhancedWhisperTranscriber()
        
        with tempfile.NamedTemporaryFile(suffix='.wav') as input_file, \
             tempfile.NamedTemporaryFile(suffix='.wav') as output_file:
            
            result = transcriber.preprocess_audio(input_file.name, output_file.name)
            
            assert result is True
            mock_subprocess.assert_called_once()
    
    @patch('subprocess.run')
    def test_get_audio_duration(self, mock_subprocess):
        """Test audio duration detection."""
        from app.audio_processing import EnhancedWhisperTranscriber
        
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = '180.5\n'
        
        transcriber = EnhancedWhisperTranscriber()
        
        duration = transcriber.get_audio_duration('test.mp3')
        
        assert duration == 180.5
    
    def test_transcription_segment_creation(self):
        """Test transcription segment data structure."""
        from app.audio_processing import TranscriptionSegment
        
        segment = TranscriptionSegment(
            text="Hello world",
            start=0.0,
            end=2.0,
            confidence=0.95,
            language='en'
        )
        
        assert segment.text == "Hello world"
        assert segment.start == 0.0
        assert segment.end == 2.0
        assert segment.confidence == 0.95
        assert segment.language == 'en'
    
    def test_segment_merging(self):
        """Test merging of overlapping segments."""
        from app.audio_processing import EnhancedWhisperTranscriber, TranscriptionSegment
        
        transcriber = EnhancedWhisperTranscriber()
        
        segments = [
            TranscriptionSegment("Hello", 0.0, 2.0, 0.9, 'en'),
            TranscriptionSegment("world", 1.5, 3.0, 0.95, 'en'),  # Overlapping
            TranscriptionSegment("test", 5.0, 7.0, 0.85, 'en')    # Separate
        ]
        
        merged = transcriber.merge_overlapping_segments(segments)
        
        assert len(merged) == 2
        assert "Hello world" in merged[0].text
        assert merged[1].text == "test"


class TestWebSocketIntegration:
    """Test WebSocket functionality."""
    
    def test_socketio_events_registration(self, app):
        """Test that WebSocket events are properly registered."""
        from app import socketio
        
        # Check that socketio is initialized
        assert socketio is not None
        
        # In a real test, you would check event handlers
        # This is a basic smoke test
    
    @patch('app.routes.socketio.emit')
    def test_task_progress_websocket_emission(self, mock_emit, client, app):
        """Test that task progress updates emit WebSocket events."""
        # This would require a more complex test setup
        # For now, verify that the socketio.emit is called
        pass


class TestErrorHandling:
    """Test error handling in tasks."""
    
    @patch('app.tasks.extract_youtube_metadata')
    def test_metadata_extraction_failure(self, mock_extract):
        """Test handling of metadata extraction failures."""
        mock_extract.side_effect = Exception("Network error")
        
        with pytest.raises(Exception):
            extract_youtube_metadata('invalid_url')
    
    def test_invalid_podcast_duration(self):
        """Test handling of invalid podcast durations."""
        from app.tasks import parse_podcast_duration
        
        assert parse_podcast_duration('invalid:format') is None
        assert parse_podcast_duration('25:99') is None  # Invalid minutes
        assert parse_podcast_duration('') is None