import pytest
import json
from unittest.mock import patch, MagicMock
from app.models import db, Channel, Video, ProcessingTask, Transcript


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_ping_endpoint(self, client):
        """Test the ping endpoint."""
        response = client.get('/api/ping')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'pong'
        assert 'timestamp' in data
    
    def test_health_endpoint_healthy(self, client):
        """Test health endpoint when system is healthy."""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'version' in data
        assert 'services' in data
        assert data['services']['database'] == 'healthy'
    
    @patch('app.routes.db.session.execute')
    def test_health_endpoint_unhealthy(self, mock_execute, client):
        """Test health endpoint when database is unhealthy."""
        mock_execute.side_effect = Exception("Database connection failed")
        
        response = client.get('/api/health')
        
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['status'] == 'unhealthy'
        assert data['services']['database'] == 'unhealthy'


class TestProcessingEndpoints:
    """Test video processing endpoints."""
    
    @patch('app.routes.extract_video_info')
    @patch('app.routes.threading.Thread')
    def test_process_video_success(self, mock_thread, mock_extract_info, client, app, sample_video_data):
        """Test successful video processing request."""
        mock_extract_info.return_value = sample_video_data['video_info']
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        response = client.post('/api/process/video', 
                              json={'url': sample_video_data['url']})
        
        assert response.status_code == 202
        data = json.loads(response.data)
        assert 'task_id' in data
        assert data['status'] == 'queued'
        assert data['message'] == 'Video processing started'
        
        # Verify thread was started
        mock_thread_instance.start.assert_called_once()
    
    def test_process_video_missing_url(self, client):
        """Test processing request without URL."""
        response = client.post('/api/process/video', json={})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'URL is required' in data['error']
    
    def test_process_video_invalid_url(self, client):
        """Test processing request with invalid URL."""
        response = client.post('/api/process/video', 
                              json={'url': 'not-a-valid-url'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid URL format' in data['error']
    
    @patch('app.routes.extract_video_info')
    def test_process_video_already_exists_completed(self, mock_extract_info, client, app, sample_video_data, sample_channel_data):
        """Test processing request for already completed video."""
        with app.app_context():
            # Create channel and video
            channel = Channel(**sample_channel_data)
            db.session.add(channel)
            db.session.flush()
            
            video = Video(
                title=sample_video_data['video_info']['title'],
                external_id=sample_video_data['video_info']['id'],
                url=sample_video_data['url'],
                channel_id=channel.id,
                processing_status='completed'
            )
            db.session.add(video)
            db.session.commit()
        
        mock_extract_info.return_value = sample_video_data['video_info']
        
        response = client.post('/api/process/video', 
                              json={'url': sample_video_data['url']})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'completed'
        assert 'video_id' in data
    
    def test_get_task_status_not_found(self, client):
        """Test getting status for non-existent task."""
        response = client.get('/api/tasks/non-existent-id')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Task not found'
    
    def test_get_task_status_success(self, client, app):
        """Test getting task status successfully."""
        with app.app_context():
            task = ProcessingTask(
                task_type='transcription',
                status='processing',
                progress=50.0,
                input_data={'url': 'https://example.com/video'}
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        response = client.get(f'/api/tasks/{task_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['task_id'] == task_id
        assert data['status'] == 'processing'
        assert data['progress'] == 50.0
        assert data['task_type'] == 'transcription'


class TestDataRetrievalEndpoints:
    """Test data retrieval endpoints."""
    
    def test_get_videos_empty(self, client):
        """Test getting videos when none exist."""
        response = client.get('/api/videos')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['videos'] == []
        assert 'pagination' in data
        assert data['pagination']['total'] == 0
    
    def test_get_videos_with_data(self, client, app, sample_channel_data, sample_video_data):
        """Test getting videos with existing data."""
        with app.app_context():
            channel = Channel(**sample_channel_data)
            db.session.add(channel)
            db.session.flush()
            
            video = Video(
                title=sample_video_data['video_info']['title'],
                external_id=sample_video_data['video_info']['id'],
                url=sample_video_data['url'],
                channel_id=channel.id,
                processing_status='completed'
            )
            db.session.add(video)
            db.session.commit()
        
        response = client.get('/api/videos')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['videos']) == 1
        assert data['videos'][0]['title'] == sample_video_data['video_info']['title']
        assert data['videos'][0]['processing_status'] == 'completed'
        assert 'channel' in data['videos'][0]
    
    def test_get_videos_with_status_filter(self, client, app, sample_channel_data, sample_video_data):
        """Test getting videos with status filter."""
        with app.app_context():
            channel = Channel(**sample_channel_data)
            db.session.add(channel)
            db.session.flush()
            
            # Create completed video
            video1 = Video(
                title="Completed Video",
                external_id="completed123",
                url="https://example.com/completed",
                channel_id=channel.id,
                processing_status='completed'
            )
            
            # Create pending video
            video2 = Video(
                title="Pending Video",
                external_id="pending123",
                url="https://example.com/pending",
                channel_id=channel.id,
                processing_status='pending'
            )
            
            db.session.add_all([video1, video2])
            db.session.commit()
        
        # Test filter for completed videos
        response = client.get('/api/videos?status=completed')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['videos']) == 1
        assert data['videos'][0]['title'] == "Completed Video"
    
    def test_get_video_transcripts_not_found(self, client):
        """Test getting transcripts for non-existent video."""
        response = client.get('/api/videos/non-existent-id/transcripts')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Video not found'
    
    def test_get_video_transcripts_success(self, client, app, sample_channel_data, sample_video_data):
        """Test getting transcripts successfully."""
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
            
            transcript1 = Transcript(
                text="First transcript segment",
                start_time=0.0,
                end_time=5.0,
                video_id=video.id
            )
            
            transcript2 = Transcript(
                text="Second transcript segment",
                start_time=5.0,
                end_time=10.0,
                video_id=video.id
            )
            
            db.session.add_all([transcript1, transcript2])
            db.session.commit()
            video_id = video.id
        
        response = client.get(f'/api/videos/{video_id}/transcripts')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['video_id'] == video_id
        assert len(data['transcripts']) == 2
        assert data['transcripts'][0]['text'] == "First transcript segment"
        assert data['transcripts'][0]['start_time'] == 0.0
        assert data['transcripts'][1]['text'] == "Second transcript segment"
    
    def test_get_channels_empty(self, client):
        """Test getting channels when none exist."""
        response = client.get('/api/channels')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['channels'] == []
    
    def test_get_channels_with_data(self, client, app, sample_channel_data):
        """Test getting channels with existing data."""
        with app.app_context():
            channel = Channel(**sample_channel_data)
            db.session.add(channel)
            db.session.commit()
        
        response = client.get('/api/channels')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['channels']) == 1
        assert data['channels'][0]['name'] == sample_channel_data['name']
        assert data['channels'][0]['platform'] == sample_channel_data['platform']


class TestErrorHandling:
    """Test error handling."""
    
    def test_404_error_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/api/non-existent-endpoint')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Not found'
    
    @patch('app.routes.Video.query')
    def test_500_error_handler(self, mock_query, client):
        """Test 500 error handler."""
        # Make the query raise an exception
        mock_query.side_effect = Exception("Database error")
        
        response = client.get('/api/videos')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['error'] == 'Internal server error'