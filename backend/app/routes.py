import datetime
import os
import uuid
import logging
from urllib.parse import urlparse

from flask import Blueprint, request, jsonify, current_app
from flask_socketio import emit
from celery.result import AsyncResult

from .models import db, Video, Channel, ProcessingTask, Transcript, Entity, EntityMention, Topic, TopicAssignment, Embedding, EmotionAnalysis
from . import socketio

api = Blueprint('api', __name__)
# Health Check Endpoints
@api.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint."""
    try:
        # Test database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        db_status = 'healthy'
    except Exception as e:
        current_app.logger.error(f"Database health check failed: {str(e)}")
        db_status = 'unhealthy'
    
    # Check model readiness
    from .tasks import check_models_ready
    models_status = check_models_ready()
    
    # Determine overall model health
    ready_models = sum(models_status.values())
    total_models = len(models_status)
    models_health = 'healthy' if ready_models == total_models else 'degraded' if ready_models > 0 else 'unhealthy'
    
    # Overall system health
    overall_status = 'healthy' if db_status == 'healthy' and models_health == 'healthy' else 'unhealthy'
    
    health_data = {
        'status': overall_status,
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'services': {
            'database': db_status,
            'models': {
                'status': models_health,
                'ready_count': f"{ready_models}/{total_models}",
                'details': models_status
            }
        }
    }
    
    status_code = 200 if health_data['status'] == 'healthy' else 503
    return jsonify(health_data), status_code

@api.route('/ping', methods=['GET'])
def ping():
    """Simple ping endpoint."""
    return jsonify({
        'message': 'pong',
        'timestamp': datetime.datetime.utcnow().isoformat()
    })

@api.route('/debug', methods=['GET'])
def debug():
    """Debug endpoint to test code reloading."""
    return jsonify({
        'message': 'Debug route loaded successfully!',
        'timestamp': datetime.datetime.utcnow().isoformat()
    })

@api.route('/test-now', methods=['POST'])
def test_queue_now():
    """NEW TEST: Bypass all caching issues and test queue processing directly."""
    try:
        data = request.get_json()
        url = data.get('url', 'https://test.com')
        
        # Create task directly in database
        task = ProcessingTask(
            task_type='transcription',
            status='queued',
            input_data={'url': url, 'test': True}
        )
        
        db.session.add(task)
        db.session.commit()
        
        # Send to Celery worker
        from .tasks import transcribe_video
        celery_task = transcribe_video.apply_async(args=[task.id, url])
        
        return jsonify({
            'success': True,
            'message': 'NEW ROUTE: Task created successfully!',
            'task_id': task.id,
            'celery_task_id': celery_task.id
        }), 202
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/test/metadata', methods=['POST'])
def test_metadata():
    """Test metadata extraction endpoint."""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url = data['url']
        
        from .tasks import extract_youtube_metadata, detect_platform
        
        platform = detect_platform(url)
        metadata = extract_youtube_metadata(url)
        
        return jsonify({
            'platform': platform,
            'title': metadata.get('title', 'Unknown'),
            'video_id': metadata.get('id', 'Unknown'),
            'status': 'success'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/test/file-ops', methods=['POST'])
def test_file_operations():
    """Test file operations that might be causing Errno 22."""
    try:
        import os
        import tempfile
        import yt_dlp
        
        # Test 1: Basic file operations
        test_dir = os.path.join(current_app.root_path, 'data')
        os.makedirs(test_dir, exist_ok=True)
        
        test_file = os.path.join(test_dir, 'test_file.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        os.remove(test_file)
        
        # Test 2: yt-dlp with a very simple URL
        data = request.get_json()
        if data and 'url' in data:
            url = data['url']
            
            ydl_opts = {
                'format': 'worst',  # Get the smallest file
                'outtmpl': os.path.join(test_dir, 'test_%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)  # Just extract info, don't download
                    
                return jsonify({
                    'file_ops': 'success',
                    'yt_dlp_info': 'success',
                    'video_title': info.get('title', 'Unknown'),
                    'video_id': info.get('id', 'Unknown'),
                    'test_dir': test_dir
                })
            except Exception as ytdl_error:
                return jsonify({
                    'file_ops': 'success', 
                    'yt_dlp_error': str(ytdl_error),
                    'error_type': type(ytdl_error).__name__
                })
        else:
            return jsonify({'file_ops': 'success', 'message': 'No URL provided for yt-dlp test'})
            
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc()
        }), 500

# Processing Endpoints
@api.route('/process/video', methods=['POST'])
def process_video():
    """Process a video URL for transcription using Celery."""
    try:
        print("DEBUG: Endpoint called")
        data = request.get_json()
        print(f"DEBUG: Got data: {data}")
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required in request body'}), 400
        
        url = data['url']
        priority = data.get('priority', 'normal')  # low, normal, high
        print(f"DEBUG: Processing URL: {url}, Priority: {priority}")
        
        # Validate URL format
        try:
            print("DEBUG: Validating URL format")
            parsed_url = urlparse(url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                return jsonify({'error': 'Invalid URL format'}), 400
            print("DEBUG: URL format valid")
        except Exception:
            return jsonify({'error': 'Invalid URL format'}), 400
        
        print("DEBUG: Creating processing task")
        # Create new processing task without metadata extraction
        task = ProcessingTask(
            task_type='transcription',
            status='queued',
            input_data={'url': url, 'priority': priority}
        )
        
        print("DEBUG: Adding task to database")
        db.session.add(task)
        db.session.commit()
        print(f"DEBUG: Task created with ID: {task.id}")
        
        # Start Celery task with priority
        from .tasks import transcribe_video
        priority_map = {'low': 3, 'normal': 6, 'high': 9}
        
        try:
            celery_task = transcribe_video.apply_async(
                args=[task.id, url],
                priority=priority_map.get(priority, 6)
            )
            
            # Store Celery task ID for monitoring
            task.input_data = task.input_data or {}
            task.input_data['celery_task_id'] = celery_task.id
            db.session.commit()
            
            celery_task_id = celery_task.id
        except Exception as e:
            current_app.logger.error(f"Failed to create Celery task: {str(e)}")
            # Fallback: create task anyway for UI tracking
            celery_task_id = f"failed-{task.id}"
        
        return jsonify({
            'task_id': task.id,
            'status': 'queued',
            'message': 'Video processing started - worker will handle transcription',
            'celery_task_id': celery_task_id
        }), 202
        
    except Exception as e:
        current_app.logger.error(f"Error processing video request: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@api.route('/process/batch', methods=['POST'])
def process_batch():
    """Process multiple videos in batch."""
    try:
        data = request.get_json()
        if not data or 'urls' not in data:
            return jsonify({'error': 'URLs array is required in request body'}), 400
        
        urls = data['urls']
        if not isinstance(urls, list) or len(urls) == 0:
            return jsonify({'error': 'URLs must be a non-empty array'}), 400
        
        if len(urls) > 50:  # Limit batch size
            return jsonify({'error': 'Maximum 50 URLs per batch'}), 400
        
        tasks = []
        
        for i, url in enumerate(urls):
            # Create processing task
            task = ProcessingTask(
                task_type='transcription',
                status='queued',
                input_data={'url': url, 'batch_index': i}
            )
            
            db.session.add(task)
            db.session.flush()  # Get task ID
            
            # Start Celery task with lower priority for batch processing
            from .tasks import transcribe_video
            celery_task = transcribe_video.apply_async(
                args=[task.id, url],
                priority=3  # Lower priority for batch
            )
            
            task.input_data['celery_task_id'] = celery_task.id
            tasks.append({
                'task_id': task.id,
                'url': url,
                'celery_task_id': celery_task.id
            })
        
        db.session.commit()
        
        return jsonify({
            'batch_id': str(uuid.uuid4()),
            'tasks': tasks,
            'message': f'Batch processing started for {len(urls)} videos'
        }), 202
        
    except Exception as e:
        current_app.logger.error(f"Error processing batch request: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get processing task status with Celery integration."""
    try:
        task = db.session.get(ProcessingTask, task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        response = {
            'task_id': task.id,
            'status': task.status,
            'progress': task.progress,
            'task_type': task.task_type,
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        }
        
        # Add Celery task information if available
        if task.input_data and 'celery_task_id' in task.input_data:
            celery_task_id = task.input_data['celery_task_id']
            celery_result = AsyncResult(celery_task_id)
            
            response['celery'] = {
                'task_id': celery_task_id,
                'state': celery_result.state,
                'info': celery_result.info if celery_result.info else {}
            }
            
            # If Celery has more recent progress info, use it
            if celery_result.state == 'PROGRESS' and celery_result.info:
                if 'progress' in celery_result.info:
                    response['progress'] = celery_result.info['progress']
                if 'message' in celery_result.info:
                    response['current_step'] = celery_result.info['message']
        
        if task.error_message:
            response['error'] = task.error_message
            
        if task.result_data:
            response['result'] = task.result_data
            
        if task.video_id:
            video = db.session.get(Video, task.video_id)
            if video:
                response['video'] = {
                    'id': video.id,
                    'title': video.title,
                    'external_id': video.external_id,
                    'processing_status': video.processing_status,
                    'platform': video.channel.platform if video.channel else None
                }
        
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error getting task status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@api.route('/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """Cancel a running task."""
    try:
        task = db.session.get(ProcessingTask, task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        if task.status not in ['queued', 'processing']:
            return jsonify({'error': 'Task cannot be cancelled'}), 400
        
        # Cancel Celery task if available
        if task.input_data and 'celery_task_id' in task.input_data:
            celery_task_id = task.input_data['celery_task_id']
            from .celery_app import celery
            celery.control.revoke(celery_task_id, terminate=True)
        
        # Update task status
        task.status = 'cancelled'
        task.completed_at = datetime.datetime.utcnow()
        task.error_message = 'Task cancelled by user'
        db.session.commit()
        
        # Emit WebSocket event
        socketio.emit('task_cancelled', {
            'task_id': task.id,
            'status': 'cancelled'
        }, room=f'task_{task.id}')
        
        return jsonify({
            'task_id': task.id,
            'status': 'cancelled',
            'message': 'Task cancelled successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error cancelling task: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@api.route('/tasks', methods=['GET'])
def get_tasks():
    """Get list of tasks with filtering."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status')
        task_type = request.args.get('task_type')
        
        query = ProcessingTask.query
        
        if status:
            query = query.filter_by(status=status)
        if task_type:
            query = query.filter_by(task_type=task_type)
            
        tasks = query.order_by(ProcessingTask.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'tasks': [{
                'id': task.id,
                'task_type': task.task_type,
                'status': task.status,
                'progress': task.progress,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'input_data': task.input_data,
                'video_id': task.video_id
            } for task in tasks.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': tasks.total,
                'pages': tasks.pages,
                'has_next': tasks.has_next,
                'has_prev': tasks.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting tasks: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Data Retrieval Endpoints
@api.route('/videos', methods=['GET'])
def get_videos():
    """Get list of processed videos."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status')
        
        query = Video.query
        
        if status:
            query = query.filter_by(processing_status=status)
            
        videos = query.order_by(Video.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'videos': [{
                'id': video.id,
                'title': video.title,
                'external_id': video.external_id,
                'url': video.url,
                'duration': video.duration,
                'processing_status': video.processing_status,
                'created_at': video.created_at.isoformat(),
                'processed_at': video.processed_at.isoformat() if video.processed_at else None,
                'channel': {
                    'id': video.channel.id,
                    'name': video.channel.name,
                    'platform': video.channel.platform
                }
            } for video in videos.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': videos.total,
                'pages': videos.pages,
                'has_next': videos.has_next,
                'has_prev': videos.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting videos: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api.route('/videos/<video_id>/transcripts', methods=['GET'])
def get_video_transcripts(video_id):
    """Get transcripts for a specific video."""
    try:
        video = db.session.get(Video, video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        transcripts = Transcript.query.filter_by(video_id=video_id).order_by(Transcript.start_time).all()
        
        return jsonify({
            'video_id': video_id,
            'video_title': video.title,
            'transcripts': [{
                'id': transcript.id,
                'text': transcript.text,
                'start_time': transcript.start_time,
                'end_time': transcript.end_time,
                'confidence': transcript.confidence,
                'speaker': transcript.speaker
            } for transcript in transcripts]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting video transcripts: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api.route('/channels', methods=['GET'])
def get_channels():
    """Get list of channels."""
    try:
        channels = Channel.query.filter_by(is_active=True).order_by(Channel.name).all()
        
        return jsonify({
            'channels': [{
                'id': channel.id,
                'name': channel.name,
                'platform': channel.platform,
                'external_id': channel.external_id,
                'url': channel.url,
                'video_count': len(channel.videos),
                'created_at': channel.created_at.isoformat()
            } for channel in channels]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting channels: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Direct Processing (Legacy Style)
@api.route('/process/direct', methods=['POST'])
def process_video_direct():
    """Process a video directly without Celery - inspired by legacy code."""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required in request body'}), 400
        
        url = data['url']
        
        # Import the necessary functions
        from .tasks import extract_youtube_metadata, get_whisper_model
        import yt_dlp
        import os
        import uuid
        
        # Step 1: Extract metadata (like legacy code)
        current_app.logger.info(f"Processing video directly: {url}")
        metadata = extract_youtube_metadata(url)
        
        # Step 2: Check if video already exists
        existing_video = Video.query.filter_by(
            external_id=metadata['id'],
            platform=metadata['platform']
        ).first()
        
        if existing_video and existing_video.processing_status == 'completed':
            return jsonify({
                'video_id': existing_video.id,
                'message': 'Video already processed',
                'status': 'completed'
            }), 200
        
        # Step 3: Create or get channel
        channel = Channel.query.filter_by(
            external_id=metadata.get('uploader_id', 'unknown'),
            platform=metadata['platform']
        ).first()
        
        if not channel:
            channel = Channel(
                name=metadata.get('uploader', 'Unknown Channel'),
                platform=metadata['platform'],
                external_id=metadata.get('uploader_id', 'unknown'),
                url=metadata.get('channel_url', ''),
                description='Auto-created channel'
            )
            db.session.add(channel)
            db.session.flush()
        
        # Step 4: Create video record
        if not existing_video:
            video = Video(
                title=metadata['title'],
                external_id=metadata['id'],
                url=url,
                platform=metadata['platform'],
                description=metadata.get('description', ''),
                duration=metadata.get('duration'),
                published_at=datetime.datetime.strptime(metadata['upload_date'], '%Y%m%d') if metadata.get('upload_date') else None,
                view_count=metadata.get('view_count'),
                like_count=metadata.get('like_count'),
                comment_count=metadata.get('comment_count'),
                language=metadata.get('language'),
                processing_status='processing',
                channel_id=channel.id
            )
            db.session.add(video)
            db.session.flush()
        else:
            video = existing_video
            video.processing_status = 'processing'
        
        db.session.commit()
        
        # Step 5: Download audio (legacy style)
        video_id = metadata['id']
        current_app.logger.info(f"Starting audio download for video ID: {video_id}")
        
        # Use the existing data directory in backend folder
        data_dir = os.path.join(current_app.root_path, 'data')
        current_app.logger.info(f"Using data directory: {data_dir}")
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        current_app.logger.info("Data directory ready")
        
        ydl_opts = {
            'format': 'bestaudio/best',  # Simplified format - get any available audio
            'outtmpl': os.path.join(data_dir, f"{video_id}.%(ext)s"),
            'quiet': False,  # Enable all output to see what's happening
            'no_warnings': False,
            'extract_flat': False,
        }
        
        try:
            current_app.logger.info(f"Downloading audio to: {data_dir}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            current_app.logger.info("yt-dlp download completed successfully")
        except Exception as download_error:
            current_app.logger.error(f"yt-dlp download error: {str(download_error)}")
            raise Exception(f"Audio download failed: {str(download_error)}")
            
        # Find the actual downloaded file
        import glob
        audio_files = glob.glob(os.path.join(data_dir, f"{video_id}.*"))
        current_app.logger.info(f"Looking for files matching: {os.path.join(data_dir, f'{video_id}.*')}")
        current_app.logger.info(f"Found files: {audio_files}")
        
        if not audio_files:
            # List all files in data dir for debugging
            all_files = os.listdir(data_dir)
            current_app.logger.error(f"No audio file found for {video_id}. Files in data dir: {all_files}")
            raise Exception(f"No audio file found for {video_id}. Expected pattern: {video_id}.*")
        
        audio_file = audio_files[0]
        current_app.logger.info(f"Found audio file: {audio_file}")
        
        # Step 6: Transcribe (legacy style)
        current_app.logger.info("Starting transcription...")
        whisper_model = get_whisper_model('medium')
        segments, info = whisper_model.transcribe(audio_file)
        
        # Step 7: Save transcripts
        transcript_count = 0
        for segment in segments:
            transcript = Transcript(
                text=segment.text.strip(),
                start_time=segment.start,
                end_time=segment.end,
                confidence=getattr(segment, 'avg_logprob', 0.0),
                model_version='medium',
                language_detected=info.language,
                video_id=video.id
            )
            db.session.add(transcript)
            transcript_count += 1
        
        # Step 8: Cleanup audio file (legacy style)
        try:
            os.remove(audio_file)
            current_app.logger.info(f"Cleaned up audio file: {audio_file}")
        except Exception as e:
            current_app.logger.warning(f"Failed to cleanup audio file: {e}")
        
        # Step 9: Update video status
        video.processing_status = 'completed'
        video.processed_at = datetime.datetime.utcnow()
        video.audio_file_path = None  # File was cleaned up
        
        db.session.commit()
        
        current_app.logger.info(f"Processing completed. Saved {transcript_count} transcript segments.")
        
        return jsonify({
            'video_id': video.id,
            'title': video.title,
            'transcript_segments': transcript_count,
            'status': 'completed',
            'message': 'Video processed successfully'
        }), 200
        
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in direct processing: {str(e)}")
        current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

# Phase 3: Content Intelligence API Endpoints

# Entity Recognition Endpoints
@api.route('/entities', methods=['GET'])
def get_entities():
    """Get list of all extracted entities with filtering."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        entity_type = request.args.get('type')
        min_confidence = request.args.get('min_confidence', type=float)
        search = request.args.get('search')
        
        query = Entity.query
        
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        if min_confidence:
            query = query.filter(Entity.confidence_score >= min_confidence)
        if search:
            query = query.filter(Entity.name.ilike(f'%{search}%'))
            
        entities = query.order_by(Entity.mention_count.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'entities': [{
                'id': entity.id,
                'name': entity.name,
                'entity_type': entity.entity_type,
                'canonical_name': entity.canonical_name,
                'description': entity.description,
                'confidence_score': entity.confidence_score,
                'mention_count': entity.mention_count,
                'created_at': entity.created_at.isoformat()
            } for entity in entities.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': entities.total,
                'pages': entities.pages,
                'has_next': entities.has_next,
                'has_prev': entities.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting entities: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@api.route('/videos/<video_id>/entities', methods=['GET'])
def get_video_entities(video_id):
    """Get entities mentioned in a specific video."""
    try:
        video = db.session.get(Video, video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        min_confidence = request.args.get('min_confidence', 0.0, type=float)
        entity_type = request.args.get('type')
        
        query = db.session.query(Entity, EntityMention).join(EntityMention).filter(
            EntityMention.video_id == video_id,
            EntityMention.confidence >= min_confidence
        )
        
        if entity_type:
            query = query.filter(Entity.entity_type == entity_type)
            
        results = query.order_by(EntityMention.confidence.desc()).all()
        
        entities = []
        for entity, mention in results:
            entities.append({
                'id': entity.id,
                'text': mention.text,
                'label': entity.entity_type,
                'confidence': mention.confidence,
                'start': mention.start_char,
                'end': mention.end_char,
                'videoId': video_id,
                'timestamp': mention.timestamp
            })
        
        return jsonify({
            'video_id': video_id,
            'video_title': video.title,
            'entities': entities
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting video entities: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# Topic Modeling Endpoints
@api.route('/topics', methods=['GET'])
def get_topics():
    """Get list of discovered topics."""
    try:
        search = request.args.get('search')
        min_coherence = request.args.get('min_coherence', type=float)
        
        query = Topic.query
        
        if search:
            query = query.filter(Topic.name.ilike(f'%{search}%'))
        if min_coherence:
            query = query.filter(Topic.coherence_score >= min_coherence)
            
        topics = query.order_by(Topic.coherence_score.desc()).all()
        
        result_topics = []
        for topic in topics:
            result_topics.append({
                'id': topic.id,
                'label': topic.name,
                'keywords': topic.keywords or [],
                'coherence': topic.coherence_score,
                'documentCount': topic.document_count,
                'evolution': []  # TODO: Implement topic evolution tracking
            })
        
        return jsonify({
            'topics': result_topics
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting topics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@api.route('/videos/<video_id>/topics', methods=['GET'])
def get_video_topics(video_id):
    """Get topics assigned to a specific video."""
    try:
        video = db.session.get(Video, video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        min_probability = request.args.get('min_probability', 0.1, type=float)
        
        results = db.session.query(Topic, TopicAssignment).join(TopicAssignment).filter(
            TopicAssignment.video_id == video_id,
            TopicAssignment.probability >= min_probability
        ).order_by(TopicAssignment.probability.desc()).all()
        
        topics = []
        for topic, assignment in results:
            topics.append({
                'id': topic.id,
                'label': topic.name,
                'keywords': topic.keywords or [],
                'coherence': topic.coherence_score,
                'probability': assignment.probability,
                'documentCount': topic.document_count
            })
        
        return jsonify({
            'video_id': video_id,
            'video_title': video.title,
            'topics': topics
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting video topics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# Vector Search Endpoints
@api.route('/search/semantic', methods=['POST'])
def semantic_search():
    """Perform semantic search using vector embeddings."""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query text is required'}), 400
        
        query = data['query']
        threshold = data.get('threshold', 0.7)
        limit = data.get('limit', 20)
        
        # Import vector search functionality
        from .vector_embeddings import VectorSearchManager
        
        search_manager = VectorSearchManager()
        results = search_manager.semantic_search(
            query_text=query,
            similarity_threshold=threshold,
            max_results=limit
        )
        
        search_results = []
        for result in results:
            search_results.append({
                'id': result.get('id'),
                'title': result.get('title', 'Unknown'),
                'similarity': result.get('similarity', 0.0),
                'snippet': result.get('content_text', '')[:200] + '...' if len(result.get('content_text', '')) > 200 else result.get('content_text', ''),
                'timestamp': result.get('timestamp'),
                'channel': result.get('channel'),
                'videoId': result.get('video_id'),
                'metadata': result.get('metadata', {})
            })
        
        return jsonify(search_results)
        
    except Exception as e:
        current_app.logger.error(f"Error in semantic search: {str(e)}")
        return jsonify({'error': 'Search failed'}), 500


@api.route('/embeddings', methods=['GET'])
def get_embeddings():
    """Get information about available embeddings."""
    try:
        video_id = request.args.get('video_id')
        
        query = Embedding.query
        if video_id:
            query = query.filter_by(video_id=video_id)
            
        embeddings = query.order_by(Embedding.created_at.desc()).limit(100).all()
        
        return jsonify({
            'embeddings': [{
                'id': emb.id,
                'model_name': emb.model_name,
                'model_version': emb.model_version,
                'dimension': emb.dimension,
                'content_type': emb.content_type,
                'video_id': emb.video_id,
                'created_at': emb.created_at.isoformat()
            } for emb in embeddings]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting embeddings: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# Emotion Analysis Endpoints
@api.route('/emotions', methods=['GET'])
def get_emotions():
    """Get emotion analysis data."""
    try:
        video_id = request.args.get('video_id')
        
        query = EmotionAnalysis.query
        if video_id:
            query = query.filter_by(video_id=video_id)
            
        emotions = query.order_by(EmotionAnalysis.start_time).all()
        
        return jsonify({
            'emotions': [{
                'id': emotion.id,
                'emotions': emotion.emotions,
                'dominant_emotion': emotion.dominant_emotion,
                'confidence_score': emotion.confidence_score,
                'start_time': emotion.start_time,
                'end_time': emotion.end_time,
                'video_id': emotion.video_id
            } for emotion in emotions]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting emotions: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@api.route('/videos/<video_id>/emotions', methods=['GET'])
def get_video_emotions(video_id):
    """Get emotion analysis for a specific video."""
    try:
        video = db.session.get(Video, video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        emotions = EmotionAnalysis.query.filter_by(video_id=video_id).order_by(EmotionAnalysis.start_time).all()
        
        # Process emotions for frontend format
        emotion_scores = []
        timeline = []
        
        for emotion in emotions:
            # Add to timeline
            timeline.append({
                'timestamp': emotion.start_time,
                'emotions': [
                    {'emotion': k, 'score': v} 
                    for k, v in emotion.emotions.items()
                ],
                'dominantEmotion': emotion.dominant_emotion
            })
            
            # Aggregate scores
            for emotion_name, score in emotion.emotions.items():
                emotion_scores.append({
                    'emotion': emotion_name,
                    'score': score,
                    'timestamp': emotion.start_time
                })
        
        return jsonify({
            'video_id': video_id,
            'video_title': video.title,
            'emotions': emotion_scores,
            'timeline': timeline
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting video emotions: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# Content Intelligence Processing Endpoints
@api.route('/videos/<video_id>/process-intelligence', methods=['POST'])
def process_video_intelligence(video_id):
    """Trigger content intelligence processing for a video."""
    try:
        # Check if models are ready before accepting task
        from .tasks import check_models_ready
        models_status = check_models_ready()
        
        # Check if required models are loaded
        required_models = ['entity_recognition', 'topic_modeling', 'vector_embeddings']
        unready_models = [model for model in required_models if not models_status.get(model, False)]
        
        if unready_models:
            return jsonify({
                'error': 'Required models not ready',
                'unready_models': unready_models,
                'message': 'Please wait for models to load or restart the service'
            }), 503
        
        video = db.session.get(Video, video_id)
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        if video.processing_status != 'completed':
            return jsonify({'error': 'Video must be fully processed before intelligence analysis'}), 400
        
        # Create processing task
        task = ProcessingTask(
            task_type='content_intelligence',
            status='queued',
            input_data={'video_id': video_id},
            video_id=video_id
        )
        
        db.session.add(task)
        db.session.commit()
        
        # Start Celery task
        from .tasks import process_content_intelligence
        celery_task = process_content_intelligence.delay(video_id)
        
        task.input_data['celery_task_id'] = celery_task.id
        db.session.commit()
        
        return jsonify({
            'task_id': task.id,
            'status': 'queued',
            'message': 'Content intelligence processing started',
            'celery_task_id': celery_task.id
        }), 202
        
    except Exception as e:
        current_app.logger.error(f"Error starting intelligence processing: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# Network Analysis Endpoints
@api.route('/network/entities', methods=['GET'])
def get_entity_network():
    """Get entity relationship network data for graph visualization."""
    try:
        min_cooccurrence = request.args.get('min_cooccurrence', 2, type=int)
        entity_types = request.args.get('types', '').split(',') if request.args.get('types') else []
        
        # Build query for entity mentions with co-occurrence analysis
        from sqlalchemy import text, func
        
        # Get entity co-occurrences within the same video with metadata
        cooccurrence_query = text("""
            SELECT 
                e1.id as entity1_id,
                e1.name as entity1_name,
                e1.entity_type as entity1_type,
                e1.canonical_name as entity1_canonical,
                e1.mention_count as entity1_mentions,
                e2.id as entity2_id,
                e2.name as entity2_name,
                e2.entity_type as entity2_type,
                e2.canonical_name as entity2_canonical,
                e2.mention_count as entity2_mentions,
                COUNT(DISTINCT em1.video_id) as cooccurrence_count,
                AVG(em1.confidence * em2.confidence) as avg_confidence,
                GROUP_CONCAT(DISTINCT v.title) as shared_videos,
                GROUP_CONCAT(DISTINCT v.id) as shared_video_ids
            FROM entities e1
            JOIN entity_mentions em1 ON e1.id = em1.entity_id
            JOIN entity_mentions em2 ON em1.video_id = em2.video_id AND em1.entity_id < em2.entity_id
            JOIN entities e2 ON em2.entity_id = e2.id
            JOIN videos v ON em1.video_id = v.id
            GROUP BY e1.id, e2.id
            HAVING COUNT(DISTINCT em1.video_id) >= :min_cooccurrence
            ORDER BY cooccurrence_count DESC
            LIMIT 500
        """)
        
        result = db.session.execute(cooccurrence_query, {'min_cooccurrence': min_cooccurrence})
        relationships = result.fetchall()
        
        # Build nodes and edges for network graph
        nodes = {}
        edges = []
        
        for rel in relationships:
            # Filter by entity types if specified
            if entity_types and rel.entity1_type not in entity_types and rel.entity2_type not in entity_types:
                continue
                
            # Add nodes with video metadata
            if rel.entity1_id not in nodes:
                nodes[rel.entity1_id] = {
                    'id': rel.entity1_id,
                    'name': rel.entity1_name,
                    'canonical_name': rel.entity1_canonical,
                    'type': rel.entity1_type,
                    'connections': 0,
                    'total_mentions': rel.entity1_mentions,
                    'videos': set(),
                    'video_titles': set()
                }
            
            if rel.entity2_id not in nodes:
                nodes[rel.entity2_id] = {
                    'id': rel.entity2_id,
                    'name': rel.entity2_name,
                    'canonical_name': rel.entity2_canonical,
                    'type': rel.entity2_type,
                    'connections': 0,
                    'total_mentions': rel.entity2_mentions,
                    'videos': set(),
                    'video_titles': set()
                }
            
            # Add video information to both nodes
            if rel.shared_video_ids:
                video_ids = rel.shared_video_ids.split(',')
                video_titles = rel.shared_videos.split(',') if rel.shared_videos else []
                
                for vid_id in video_ids:
                    nodes[rel.entity1_id]['videos'].add(vid_id)
                    nodes[rel.entity2_id]['videos'].add(vid_id)
                
                for title in video_titles:
                    if title:
                        nodes[rel.entity1_id]['video_titles'].add(title.strip())
                        nodes[rel.entity2_id]['video_titles'].add(title.strip())
            
            # Add edge
            edges.append({
                'source': rel.entity1_id,
                'target': rel.entity2_id,
                'weight': int(rel.cooccurrence_count),
                'confidence': float(rel.avg_confidence or 0.0)
            })
            
            # Update connection counts
            nodes[rel.entity1_id]['connections'] += 1
            nodes[rel.entity2_id]['connections'] += 1
        
        # Convert sets to lists for JSON serialization
        for node in nodes.values():
            node['videos'] = list(node['videos'])
            node['video_titles'] = list(node['video_titles'])
        
        return jsonify({
            'nodes': list(nodes.values()),
            'edges': edges,
            'stats': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'min_cooccurrence_threshold': min_cooccurrence
            }
        })
        
    except Exception as e:
        import traceback
        current_app.logger.error(f"Entity network analysis failed: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Network analysis failed: {str(e)}'}), 500


@api.route('/network/entities/<entity_id>/neighbors', methods=['GET'])
def get_entity_neighbors(entity_id):
    """Get neighboring entities for a specific entity."""
    try:
        entity = db.session.get(Entity, entity_id)
        if not entity:
            return jsonify({'error': 'Entity not found'}), 404
            
        # Find entities that co-occur with this entity
        from sqlalchemy import text
        neighbors_query = text("""
            SELECT 
                e.id,
                e.name,
                e.entity_type,
                COUNT(DISTINCT em1.video_id) as cooccurrence_count,
                AVG(em1.confidence * em2.confidence) as avg_confidence,
                GROUP_CONCAT(DISTINCT v.title) as videos
            FROM entities e
            JOIN entity_mentions em1 ON e.id = em1.entity_id
            JOIN entity_mentions em2 ON em1.video_id = em2.video_id
            JOIN videos v ON em1.video_id = v.id
            WHERE em2.entity_id = :entity_id AND e.id != :entity_id
            GROUP BY e.id
            ORDER BY cooccurrence_count DESC
            LIMIT 20
        """)
        
        result = db.session.execute(neighbors_query, {'entity_id': entity_id})
        neighbors = result.fetchall()
        
        return jsonify({
            'entity': {
                'id': entity.id,
                'name': entity.name,
                'type': entity.entity_type
            },
            'neighbors': [{
                'id': n.id,
                'name': n.name,
                'type': n.entity_type,
                'cooccurrence_count': int(n.cooccurrence_count),
                'confidence': float(n.avg_confidence or 0.0),
                'shared_videos': n.videos.split(',') if n.videos else []
            } for n in neighbors]
        })
        
    except Exception as e:
        current_app.logger.error(f"Entity neighbors analysis failed: {str(e)}")
        return jsonify({'error': f'Neighbors analysis failed: {str(e)}'}), 500


# Batch Processing Endpoints
@api.route('/process/topics/batch', methods=['POST'])
def batch_process_topics():
    """Process topics across all completed videos in batch."""
    try:
        # Get all completed videos with transcripts
        videos = Video.query.filter_by(processing_status='completed').all()
        
        video_texts = []
        video_ids = []
        
        for video in videos:
            transcripts = Transcript.query.filter_by(video_id=video.id).order_by(Transcript.start_time).all()
            if transcripts:
                full_text = ' '.join([t.text for t in transcripts])
                if len(full_text) > 200:  # Only include videos with substantial content
                    video_texts.append(full_text)
                    video_ids.append(video.id)
        
        if len(video_texts) < 5:
            return jsonify({
                'error': 'Not enough videos with content for topic modeling',
                'videos_found': len(video_texts),
                'minimum_required': 5
            }), 400
        
        # Import and run topic processing
        from .tasks import process_video_topics
        current_app.logger.info(f"Starting batch topic processing for {len(video_texts)} videos")
        
        result = process_video_topics(video_texts, video_ids)
        
        return jsonify({
            'success': True,
            'videos_processed': len(video_texts),
            'topics_discovered': len(result.get('topics', [])),
            'message': f'Batch topic processing completed for {len(video_texts)} videos'
        }), 200
        
    except Exception as e:
        import traceback
        current_app.logger.error(f"Batch topic processing failed: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Batch processing failed: {str(e)}'}), 500


# Error handlers
@api.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@api.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500
