import pytest
import json
from unittest.mock import patch, MagicMock
from app.models import db, ProcessingTask, Video, Channel


class TestEnhancedProcessingEndpoints:
    """Test enhanced processing endpoints with Celery integration."""
    
    @patch('app.routes.transcribe_video.apply_async')
    @patch('app.routes.extract_metadata.delay')
    def test_process_video_with_celery(self, mock_extract_metadata, mock_transcribe, client, app):
        """Test video processing with Celery integration."""
        # Mock metadata extraction
        mock_metadata_task = MagicMock()
        mock_metadata_task.get.return_value = {
            'platform': 'youtube',
            'id': 'test123',
            'title': 'Test Video',
            'uploader': 'Test Channel',
            'uploader_id': 'UCTest123',
            'channel_url': 'https://www.youtube.com/channel/UCTest123'
        }
        mock_extract_metadata.return_value = mock_metadata_task
        
        # Mock Celery task
        mock_celery_task = MagicMock()
        mock_celery_task.id = 'celery-task-123'
        mock_transcribe.return_value = mock_celery_task
        
        response = client.post('/api/process/video', 
                              json={'url': 'https://www.youtube.com/watch?v=test123'})
        
        assert response.status_code == 202
        data = json.loads(response.data)
        
        assert 'task_id' in data
        assert 'celery_task_id' in data
        assert data['status'] == 'queued'
        assert data['message'] == 'Video processing started'
        
        # Verify Celery task was started
        mock_transcribe.assert_called_once()
    
    @patch('app.routes.extract_metadata.delay')
    def test_process_video_with_priority(self, mock_extract_metadata, client, app):
        """Test video processing with priority setting."""
        # Mock metadata extraction
        mock_metadata_task = MagicMock()
        mock_metadata_task.get.return_value = {
            'platform': 'youtube',
            'id': 'test123',
            'title': 'Test Video',
            'uploader': 'Test Channel',
            'uploader_id': 'UCTest123'
        }
        mock_extract_metadata.return_value = mock_metadata_task
        
        with patch('app.routes.transcribe_video.apply_async') as mock_transcribe:
            mock_celery_task = MagicMock()
            mock_celery_task.id = 'celery-task-123'
            mock_transcribe.return_value = mock_celery_task
            
            response = client.post('/api/process/video', 
                                  json={
                                      'url': 'https://www.youtube.com/watch?v=test123',
                                      'priority': 'high'
                                  })
            
            assert response.status_code == 202
            
            # Verify high priority was used (priority=9)
            mock_transcribe.assert_called_once()
            call_args = mock_transcribe.call_args
            assert call_args[1]['priority'] == 9
    
    def test_process_batch_videos(self, client, app):
        """Test batch video processing."""
        urls = [
            'https://www.youtube.com/watch?v=test1',
            'https://www.youtube.com/watch?v=test2',
            'https://www.youtube.com/watch?v=test3'
        ]
        
        with patch('app.routes.transcribe_video.apply_async') as mock_transcribe:
            mock_celery_task = MagicMock()
            mock_celery_task.id = 'celery-task-123'
            mock_transcribe.return_value = mock_celery_task
            
            response = client.post('/api/process/batch', json={'urls': urls})
            
            assert response.status_code == 202
            data = json.loads(response.data)
            
            assert 'batch_id' in data
            assert 'tasks' in data
            assert len(data['tasks']) == 3
            assert 'Batch processing started for 3 videos' in data['message']
            
            # Verify all tasks were created with batch priority (3)
            assert mock_transcribe.call_count == 3
            for call in mock_transcribe.call_args_list:
                assert call[1]['priority'] == 3
    
    def test_process_batch_size_limit(self, client):
        """Test batch size limitation."""
        urls = ['https://www.youtube.com/watch?v=test'] * 51  # Over limit
        
        response = client.post('/api/process/batch', json={'urls': urls})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Maximum 50 URLs per batch' in data['error']
    
    def test_process_batch_empty_urls(self, client):
        """Test batch processing with empty URLs."""
        response = client.post('/api/process/batch', json={'urls': []})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'non-empty array' in data['error']


class TestTaskManagement:
    """Test enhanced task management endpoints."""
    
    def test_get_task_status_with_celery_info(self, client, app):
        """Test task status endpoint with Celery information."""
        with app.app_context():
            task = ProcessingTask(
                task_type='transcription',
                status='processing',
                progress=50.0,
                input_data={'celery_task_id': 'celery-123'}
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        with patch('app.routes.AsyncResult') as mock_async_result:
            mock_result = MagicMock()
            mock_result.state = 'PROGRESS'
            mock_result.info = {'progress': 75.0, 'message': 'Processing chunk 3/5'}
            mock_async_result.return_value = mock_result
            
            response = client.get(f'/api/tasks/{task_id}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert data['task_id'] == task_id
            assert data['progress'] == 75.0  # Updated from Celery
            assert data['current_step'] == 'Processing chunk 3/5'
            assert 'celery' in data
            assert data['celery']['task_id'] == 'celery-123'
            assert data['celery']['state'] == 'PROGRESS'
    
    def test_cancel_task(self, client, app):
        """Test task cancellation."""
        with app.app_context():
            task = ProcessingTask(
                task_type='transcription',
                status='processing',
                input_data={'celery_task_id': 'celery-123'}
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        with patch('app.routes.celery.control.revoke') as mock_revoke:
            response = client.post(f'/api/tasks/{task_id}/cancel')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert data['status'] == 'cancelled'
            assert 'cancelled successfully' in data['message']
            
            # Verify Celery task was revoked
            mock_revoke.assert_called_once_with('celery-123', terminate=True)
            
            # Verify database was updated
            with app.app_context():
                updated_task = db.session.get(ProcessingTask, task_id)
                assert updated_task.status == 'cancelled'
                assert 'cancelled by user' in updated_task.error_message
    
    def test_cancel_completed_task(self, client, app):
        """Test cancelling an already completed task."""
        with app.app_context():
            task = ProcessingTask(
                task_type='transcription',
                status='completed',
                progress=100.0
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        response = client.post(f'/api/tasks/{task_id}/cancel')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'cannot be cancelled' in data['error']
    
    def test_get_tasks_with_filtering(self, client, app):
        """Test getting tasks with status and type filtering."""
        with app.app_context():
            # Create test tasks
            task1 = ProcessingTask(task_type='transcription', status='completed')
            task2 = ProcessingTask(task_type='transcription', status='processing')
            task3 = ProcessingTask(task_type='metadata', status='completed')
            
            db.session.add_all([task1, task2, task3])
            db.session.commit()
        
        # Test status filtering
        response = client.get('/api/tasks?status=completed')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['tasks']) == 2  # task1 and task3
        
        # Test type filtering
        response = client.get('/api/tasks?task_type=transcription')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['tasks']) == 2  # task1 and task2
        
        # Test combined filtering
        response = client.get('/api/tasks?status=processing&task_type=transcription')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['tasks']) == 1  # only task2


class TestMultiPlatformSupport:
    """Test multi-platform content support."""
    
    @patch('app.routes.extract_metadata.delay')
    def test_process_youtube_video(self, mock_extract_metadata, client):
        """Test processing YouTube video."""
        mock_metadata_task = MagicMock()
        mock_metadata_task.get.return_value = {
            'platform': 'youtube',
            'id': 'dQw4w9WgXcQ',
            'title': 'Never Gonna Give You Up',
            'uploader': 'Rick Astley',
            'uploader_id': 'UCRickAstley'
        }
        mock_extract_metadata.return_value = mock_metadata_task
        
        with patch('app.routes.transcribe_video.apply_async') as mock_transcribe:
            mock_celery_task = MagicMock()
            mock_celery_task.id = 'celery-task-123'
            mock_transcribe.return_value = mock_celery_task
            
            response = client.post('/api/process/video', 
                                  json={'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'})
            
            assert response.status_code == 202
    
    @patch('app.routes.extract_metadata.delay')
    def test_process_podcast_episode(self, mock_extract_metadata, client):
        """Test processing podcast episode."""
        mock_metadata_task = MagicMock()
        mock_metadata_task.get.return_value = {
            'platform': 'podcast',
            'id': 'episode-123',
            'title': 'Test Podcast Episode',
            'uploader': 'Test Podcast',
            'uploader_id': 'podcast-123'
        }
        mock_extract_metadata.return_value = mock_metadata_task
        
        with patch('app.routes.transcribe_video.apply_async') as mock_transcribe:
            mock_celery_task = MagicMock()
            mock_celery_task.id = 'celery-task-123'
            mock_transcribe.return_value = mock_celery_task
            
            response = client.post('/api/process/video', 
                                  json={'url': 'https://podcast.example.com/feed.rss'})
            
            assert response.status_code == 202
    
    @patch('app.routes.extract_metadata.delay')
    def test_process_twitch_video(self, mock_extract_metadata, client):
        """Test processing Twitch video."""
        mock_metadata_task = MagicMock()
        mock_metadata_task.get.return_value = {
            'platform': 'twitch',
            'id': 'twitch-123',
            'title': 'Test Stream',
            'uploader': 'test_streamer',
            'uploader_id': 'test_streamer'
        }
        mock_extract_metadata.return_value = mock_metadata_task
        
        with patch('app.routes.transcribe_video.apply_async') as mock_transcribe:
            mock_celery_task = MagicMock()
            mock_celery_task.id = 'celery-task-123'
            mock_transcribe.return_value = mock_celery_task
            
            response = client.post('/api/process/video', 
                                  json={'url': 'https://www.twitch.tv/videos/123456789'})
            
            assert response.status_code == 202


class TestErrorHandling:
    """Test error handling in enhanced routes."""
    
    @patch('app.routes.extract_metadata.delay')
    def test_metadata_extraction_timeout(self, mock_extract_metadata, client):
        """Test handling of metadata extraction timeout."""
        mock_metadata_task = MagicMock()
        mock_metadata_task.get.side_effect = Exception("Timeout")
        mock_extract_metadata.return_value = mock_metadata_task
        
        response = client.post('/api/process/video', 
                              json={'url': 'https://www.youtube.com/watch?v=invalid'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Failed to extract metadata' in data['error']
    
    def test_duplicate_video_detection(self, client, app, sample_channel_data):
        """Test duplicate video detection and handling."""
        with app.app_context():
            # Create existing channel and video
            channel = Channel(**sample_channel_data)
            db.session.add(channel)
            db.session.flush()
            
            video = Video(
                title='Existing Video',
                external_id='existing123',
                platform='youtube',
                url='https://www.youtube.com/watch?v=existing123',
                channel_id=channel.id,
                processing_status='completed'
            )
            db.session.add(video)
            db.session.commit()
        
        with patch('app.routes.extract_metadata.delay') as mock_extract_metadata:
            mock_metadata_task = MagicMock()
            mock_metadata_task.get.return_value = {
                'platform': 'youtube',
                'id': 'existing123',
                'title': 'Existing Video'
            }
            mock_extract_metadata.return_value = mock_metadata_task
            
            response = client.post('/api/process/video', 
                                  json={'url': 'https://www.youtube.com/watch?v=existing123'})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'completed'
            assert 'already processed' in data['message']


class TestWebSocketEvents:
    """Test WebSocket event emissions."""
    
    @patch('app.routes.socketio.emit')
    @patch('app.routes.extract_metadata.delay')
    def test_websocket_task_started_event(self, mock_extract_metadata, mock_emit, client):
        """Test WebSocket event emission when task starts."""
        mock_metadata_task = MagicMock()
        mock_metadata_task.get.return_value = {
            'platform': 'youtube',
            'id': 'test123',
            'title': 'Test Video',
            'uploader': 'Test Channel',
            'uploader_id': 'UCTest123'
        }
        mock_extract_metadata.return_value = mock_metadata_task
        
        with patch('app.routes.transcribe_video.apply_async') as mock_transcribe:
            mock_celery_task = MagicMock()
            mock_celery_task.id = 'celery-task-123'
            mock_transcribe.return_value = mock_celery_task
            
            response = client.post('/api/process/video', 
                                  json={'url': 'https://www.youtube.com/watch?v=test123'})
            
            assert response.status_code == 202
            
            # Verify WebSocket event was emitted
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args
            assert call_args[0][0] == 'task_started'
            assert 'task_id' in call_args[0][1]
            assert call_args[0][1]['status'] == 'queued'


class TestProgressTracking:
    """Test progress tracking functionality."""
    
    def test_progress_update_format(self, app):
        """Test progress update data format."""
        from app.tasks import update_task_progress
        
        with app.app_context():
            task = ProcessingTask(
                task_type='transcription',
                status='processing',
                progress=0.0
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
            
            # Test progress update
            update_task_progress(task_id, 50.0, 'processing', 'Downloading audio')
            
            # Verify database update
            updated_task = db.session.get(ProcessingTask, task_id)
            assert updated_task.progress == 50.0
            assert updated_task.status == 'processing'