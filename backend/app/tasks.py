"""
Celery tasks for background processing.
"""
import os
import time
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List

from celery import current_task
from faster_whisper import WhisperModel
import yt_dlp
import feedparser
import requests

from app.celery_app import celery
from app.models import db, Video, Channel, ProcessingTask, Transcript, Entity, EntityMention, Topic, Embedding
from app import create_app


# Global variables for model caching with thread safety
import threading
whisper_model = None
model_load_lock = threading.Lock()
models_ready = {
    'whisper': False,
    'entity_recognition': False,
    'topic_modeling': False,
    'vector_embeddings': False
}
logger = logging.getLogger(__name__)


def get_whisper_model(model_size: str = 'tiny'):
    """Get or create Whisper model with caching and thread safety."""
    global whisper_model
    with model_load_lock:
        if whisper_model is None:
            logger.info(f"Loading Whisper model: {model_size}")
            whisper_model = WhisperModel(model_size)
            models_ready['whisper'] = True
            logger.info(f"Whisper model {model_size} loaded successfully")
    return whisper_model


def preload_all_models():
    """Pre-load all models at startup to prevent runtime failures."""
    logger.info("Starting model pre-loading...")
    
    # Load Whisper model
    try:
        get_whisper_model('tiny')
    except Exception as e:
        logger.error(f"Failed to preload Whisper model: {str(e)}")
        models_ready['whisper'] = False
    
    # Pre-load entity recognition models (Flair German NER)
    try:
        from .entity_recognition_flair import get_entity_recognizer
        recognizer = get_entity_recognizer()
        # Test the model by processing a small sample
        test_result = recognizer.extract_entities("Test Deutschland Berlin")
        models_ready['entity_recognition'] = True
        logger.info(f"Flair entity recognition model loaded successfully: {recognizer.model_name}")
    except Exception as e:
        logger.error(f"Failed to preload Flair entity recognition model: {str(e)}")
        models_ready['entity_recognition'] = False
    
    # Pre-load topic modeling models
    try:
        from .topic_modeling import get_topic_manager
        topic_manager = get_topic_manager()
        topic_manager._setup_embedding_model()  # Force embedding model loading
        models_ready['topic_modeling'] = True
        logger.info("Topic modeling models loaded successfully")
    except Exception as e:
        logger.error(f"Failed to preload topic modeling models: {str(e)}")
        models_ready['topic_modeling'] = False
    
    # Pre-load vector embedding models
    try:
        from .vector_embeddings import VectorEmbeddingManager
        embedding_manager = VectorEmbeddingManager()
        embedding_manager.load_model('sentence-transformers/all-MiniLM-L6-v2')  # Force model loading
        models_ready['vector_embeddings'] = True
        logger.info("Vector embedding models loaded successfully")
    except Exception as e:
        logger.error(f"Failed to preload vector embedding models: {str(e)}")
        models_ready['vector_embeddings'] = False
    
    ready_count = sum(models_ready.values())
    total_models = len(models_ready)
    logger.info(f"Model preloading complete: {ready_count}/{total_models} models ready")
    return models_ready


def check_models_ready():
    """Check if all required models are loaded and ready."""
    return models_ready


def update_task_progress(task_id: str, progress: float, status: str = None, message: str = None):
    """Update task progress in database and Celery."""
    # Skip if no task_id (not running in Celery context)
    if task_id is None:
        logger.debug(f"No task_id provided, skipping progress update: {progress}% - {message}")
        return
    
    app = create_app()
    with app.app_context():
        task = db.session.get(ProcessingTask, task_id)
        if task:
            task.progress = progress
            if status:
                task.status = status
            if message:
                task.error_message = message
            db.session.commit()
    
    # Update Celery task state
    if current_task:
        current_task.update_state(
            state='PROGRESS',
            meta={'progress': progress, 'message': message or ''}
        )


def detect_platform(url: str) -> str:
    """Detect content platform from URL."""
    domain = urlparse(url).netloc.lower()
    
    if 'youtube.com' in domain or 'youtu.be' in domain:
        return 'youtube'
    elif 'twitch.tv' in domain:
        return 'twitch'
    elif any(podcast_indicator in url.lower() for podcast_indicator in ['.rss', '.xml', 'feed', 'podcast']):
        return 'podcast'
    else:
        return 'unknown'


@celery.task(bind=True, name='app.tasks.extract_metadata')
def extract_metadata(self, url: str, platform: str = None) -> Dict[str, Any]:
    """Extract metadata from various platforms."""
    try:
        if not platform:
            platform = detect_platform(url)
        
        update_task_progress(self.request.id, 10, 'processing', 'Extracting metadata')
        
        if platform == 'youtube':
            return extract_youtube_metadata(url)
        elif platform == 'podcast':
            return extract_podcast_metadata(url)
        elif platform == 'twitch':
            return extract_twitch_metadata(url)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
            
    except Exception as e:
        logger.error(f"Metadata extraction failed: {str(e)}")
        update_task_progress(self.request.id, 0, 'failed', str(e))
        raise


def extract_youtube_metadata(url: str) -> Dict[str, Any]:
    """Extract YouTube video metadata."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        return {
            'platform': 'youtube',
            'id': info.get('id'),
            'title': info.get('title'),
            'description': info.get('description'),
            'duration': info.get('duration'),
            'upload_date': info.get('upload_date'),
            'uploader': info.get('uploader'),
            'uploader_id': info.get('uploader_id'),
            'view_count': info.get('view_count'),
            'like_count': info.get('like_count'),
            'comment_count': info.get('comment_count'),
            'thumbnail': info.get('thumbnail'),
            'channel_url': info.get('channel_url'),
            'tags': info.get('tags', []),
            'categories': info.get('categories', []),
            'language': info.get('language'),
            'availability': info.get('availability'),
        }


def extract_podcast_metadata(url: str) -> Dict[str, Any]:
    """Extract podcast episode metadata from RSS feed."""
    feed = feedparser.parse(url)
    
    if not feed.entries:
        raise ValueError("No episodes found in podcast feed")
    
    # Get the latest episode
    episode = feed.entries[0]
    
    return {
        'platform': 'podcast',
        'id': episode.get('id', episode.get('link')),
        'title': episode.get('title'),
        'description': episode.get('description') or episode.get('summary'),
        'duration': parse_podcast_duration(episode.get('itunes_duration')),
        'upload_date': format_podcast_date(episode.get('published_parsed')),
        'uploader': feed.feed.get('title'),
        'uploader_id': feed.feed.get('link'),
        'channel_url': feed.feed.get('link'),
        'audio_url': extract_podcast_audio_url(episode),
        'tags': [tag.term for tag in getattr(episode, 'tags', [])],
    }


def extract_twitch_metadata(url: str) -> Dict[str, Any]:
    """Extract Twitch stream/video metadata."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        return {
            'platform': 'twitch',
            'id': info.get('id'),
            'title': info.get('title'),
            'description': info.get('description'),
            'duration': info.get('duration'),
            'upload_date': info.get('upload_date'),
            'uploader': info.get('uploader'),
            'uploader_id': info.get('uploader_id'),
            'view_count': info.get('view_count'),
            'thumbnail': info.get('thumbnail'),
            'is_live': info.get('is_live', False),
        }


def parse_podcast_duration(duration_str: str) -> Optional[int]:
    """Parse podcast duration string to seconds."""
    if not duration_str:
        return None
    
    try:
        # Handle HH:MM:SS or MM:SS format
        parts = duration_str.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return int(duration_str)
    except (ValueError, IndexError):
        return None


def format_podcast_date(date_parsed) -> Optional[str]:
    """Format podcast date to YYYYMMDD string."""
    if not date_parsed:
        return None
    
    try:
        dt = datetime(*date_parsed[:6])
        return dt.strftime('%Y%m%d')
    except (TypeError, ValueError):
        return None


def extract_podcast_audio_url(episode) -> Optional[str]:
    """Extract audio URL from podcast episode."""
    # Check enclosures for audio files
    for enclosure in getattr(episode, 'enclosures', []):
        if enclosure.type and 'audio' in enclosure.type:
            return enclosure.href
    
    # Check links for audio files
    for link in getattr(episode, 'links', []):
        if link.type and 'audio' in link.type:
            return link.href
    
    return None


@celery.task(bind=True, name='app.tasks.download_audio')
def download_audio(self, url: str, video_id: str, audio_storage_path: str) -> str:
    """Download audio from various platforms."""
    try:
        update_task_progress(self.request.id, 20, 'processing', 'Downloading audio')
        
        platform = detect_platform(url)
        
        if platform == 'podcast':
            return download_podcast_audio(url, video_id, audio_storage_path, self.request.id)
        else:
            return download_yt_dlp_audio(url, video_id, audio_storage_path, self.request.id)
            
    except Exception as e:
        logger.error(f"Audio download failed: {str(e)}")
        update_task_progress(self.request.id, 0, 'failed', str(e))
        raise


def download_podcast_audio(url: str, video_id: str, audio_storage_path: str, task_id: str) -> str:
    """Download audio from podcast RSS feed."""
    # First extract metadata to get audio URL
    feed = feedparser.parse(url)
    episode = feed.entries[0]
    audio_url = extract_podcast_audio_url(episode)
    
    if not audio_url:
        raise ValueError("No audio URL found in podcast episode")
    
    # Download the audio file
    os.makedirs(audio_storage_path, exist_ok=True)
    audio_file = os.path.join(audio_storage_path, f"{video_id}.mp3")
    
    response = requests.get(audio_url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    
    with open(audio_file, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = 20 + (downloaded / total_size) * 30  # 20-50% range
                    update_task_progress(task_id, progress, 'processing', 'Downloading audio')
    
    return audio_file


def download_yt_dlp_audio(url: str, video_id: str, audio_storage_path: str, task_id: str) -> str:
    """Download audio using yt-dlp."""
    os.makedirs(audio_storage_path, exist_ok=True)
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            if 'total_bytes' in d:
                progress = 20 + (d['downloaded_bytes'] / d['total_bytes']) * 30  # 20-50% range
                update_task_progress(task_id, progress, 'processing', 'Downloading audio')
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(audio_storage_path, f"{video_id}.%(ext)s"),
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [progress_hook],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    # Find the downloaded file
    for ext in ['mp3', 'wav', 'm4a', 'webm', 'mp4']:
        potential_file = os.path.join(audio_storage_path, f"{video_id}.{ext}")
        if os.path.exists(potential_file):
            return potential_file
    
    raise FileNotFoundError("Downloaded audio file not found")


@celery.task(bind=True, name='app.tasks.transcribe_video')
def transcribe_video(self, task_id: str, url: str) -> Dict[str, Any]:
    """Main video transcription task."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get task from database
            task = db.session.get(ProcessingTask, task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            # Update task status
            task.status = 'processing'
            task.started_at = datetime.utcnow()
            db.session.commit()
            
            # Step 1: Extract metadata - call directly instead of using .delay().get()
            update_task_progress(task_id, 5, 'processing', 'Extracting metadata')
            platform = detect_platform(url)
            if platform == 'youtube':
                metadata = extract_youtube_metadata(url)
            else:
                raise ValueError(f"Unsupported platform: {platform}")
            
            # Step 2: Create or get channel
            channel = create_or_get_channel(metadata)
            
            # Step 3: Create video record
            video = create_video_record(metadata, channel, url)
            task.video_id = video.id
            db.session.commit()
            
            # Step 4: Download audio - call directly instead of using .delay().get()
            audio_storage_path = app.config.get('AUDIO_STORAGE_PATH', './data/audio')
            platform = detect_platform(url)
            
            if platform == 'podcast':
                audio_file = download_podcast_audio(url, video.external_id, audio_storage_path, task_id)
            else:
                audio_file = download_yt_dlp_audio(url, video.external_id, audio_storage_path, task_id)
            
            video.audio_file_path = audio_file
            db.session.commit()
            
            # Step 5: Transcribe audio
            update_task_progress(task_id, 60, 'processing', 'Transcribing audio')
            transcripts = transcribe_audio_file(audio_file, video.id, task_id)
            
            # Step 6: Run content intelligence processing
            update_task_progress(task_id, 85, 'processing', 'Processing content intelligence')
            try:
                intelligence_result = process_content_intelligence_direct(video.id, task_id)
            except Exception as e:
                logger.error(f"Content intelligence processing failed: {str(e)}")
                intelligence_result = {'entities_count': 0, 'topics_count': 0, 'embeddings_generated': False, 'error': str(e)}
            
            # Step 7: Update video status
            video.processing_status = 'completed'
            video.processed_at = datetime.utcnow()
            
            # Step 8: Update task status
            update_task_progress(task_id, 100.0, 'completed', 'Processing completed successfully')
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            task.progress = 100.0
            task.result_data = {
                'video_id': video.id,
                'transcript_count': len(transcripts),
                'audio_file': audio_file,
                'entities_extracted': intelligence_result.get('entities_count', 0),
                'topics_discovered': intelligence_result.get('topics_count', 0),
                'embeddings_generated': intelligence_result.get('embeddings_generated', False)
            }
            
            db.session.commit()
            
            # Step 9: Schedule cleanup
            cleanup_files.apply_async(args=[audio_file], countdown=300)  # Clean up after 5 minutes
            
            return {
                'video_id': video.id,
                'transcript_count': len(transcripts),
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Transcription failed for task {task_id}: {str(e)}")
            
            # Update task with error
            task = db.session.get(ProcessingTask, task_id)
            if task:
                update_task_progress(task_id, task.progress, 'failed', str(e))
                task.status = 'failed'
                task.error_message = str(e)
                task.completed_at = datetime.utcnow()
                db.session.commit()
            
            raise


def create_or_get_channel(metadata: Dict[str, Any]) -> Channel:
    """Create or retrieve channel from database."""
    channel = Channel.query.filter_by(
        external_id=metadata['uploader_id'],
        platform=metadata['platform']
    ).first()
    
    if not channel:
        channel = Channel(
            name=metadata['uploader'],
            platform=metadata['platform'],
            external_id=metadata['uploader_id'],
            url=metadata.get('channel_url', ''),
        )
        db.session.add(channel)
        db.session.flush()
    
    return channel


def create_video_record(metadata: Dict[str, Any], channel: Channel, url: str) -> Video:
    """Create video record in database."""
    # Parse upload date
    published_at = None
    if metadata.get('upload_date'):
        try:
            published_at = datetime.strptime(metadata['upload_date'], '%Y%m%d')
        except ValueError:
            pass
    
    video = Video(
        title=metadata['title'],
        external_id=metadata['id'],
        url=url,
        platform=metadata['platform'],
        description=metadata.get('description'),
        thumbnail_url=metadata.get('thumbnail'),
        duration=metadata.get('duration'),
        published_at=published_at,
        view_count=metadata.get('view_count'),
        like_count=metadata.get('like_count'),
        comment_count=metadata.get('comment_count'),
        language=metadata.get('language'),
        channel_id=channel.id,
        processing_status='processing'
    )
    
    db.session.add(video)
    db.session.flush()
    return video


def transcribe_audio_file(audio_file: str, video_id: str, task_id: str) -> list:
    """Transcribe audio file using enhanced Whisper processing with LLM cleaning."""
    from .audio_processing import get_transcriber
    
    # Get transcriber with configuration
    app = create_app()
    with app.app_context():
        model_size = app.config.get('WHISPER_MODEL', 'medium')
        device = app.config.get('WHISPER_DEVICE', 'auto')
    
    transcriber = get_transcriber(model_size, device)
    
    # Progress callback function for transcription
    def progress_callback(progress, message):
        # Convert transcription progress (0-100) to overall progress (60-85)
        adjusted_progress = 60 + (progress * 0.25)
        update_task_progress(task_id, adjusted_progress, 'processing', message)
    
    # Transcribe with enhanced processing
    update_task_progress(task_id, 60, 'processing', 'Starting transcription')
    segments, info = transcriber.transcribe_file(audio_file, progress_callback)
    
    # Step: LLM cleaning of transcripts
    update_task_progress(task_id, 85, 'processing', 'Cleaning transcripts with LLM')
    cleaned_segments = clean_transcript_segments(segments, video_id, task_id)
    
    # Save cleaned transcripts to database
    transcripts = []
    total_segments = len(cleaned_segments)
    
    for i, (original_segment, cleaning_result) in enumerate(zip(segments, cleaned_segments)):
        # Use cleaned text if cleaning was successful, otherwise use original
        final_text = cleaning_result.cleaned_text if cleaning_result.hallucination_check_passed else original_segment.text
        
        transcript = Transcript(
            text=final_text,
            start_time=original_segment.start,
            end_time=original_segment.end,
            confidence=original_segment.confidence * cleaning_result.confidence_score,  # Adjust confidence
            video_id=video_id,
            model_version=f"{model_size}_llm_cleaned",  # Indicate LLM processing
            language_detected=original_segment.language or info.get('language'),
            # Store cleaning metadata
            processing_metadata={
                'original_text': original_segment.text,
                'llm_cleaned': cleaning_result.hallucination_check_passed,
                'cleaning_confidence': cleaning_result.confidence_score,
                'cleaning_warnings': cleaning_result.warnings[:3],  # Store first 3 warnings
                'changes_made': cleaning_result.changes_made[:5]  # Store first 5 changes
            }
        )
        
        db.session.add(transcript)
        transcripts.append(transcript)
        
        # Update progress for database saving
        if i % 10 == 0 or i == total_segments - 1:  # Update every 10 segments
            progress = 95 + ((i + 1) / total_segments) * 5  # 95-100% range
            update_task_progress(task_id, progress, 'processing', f'Saving cleaned segment {i+1}/{total_segments}')
    
    db.session.commit()
    
    # Log cleaning statistics
    cleaned_count = sum(1 for result in cleaned_segments if result.hallucination_check_passed)
    logger.info(f"Saved {len(transcripts)} transcript segments for video {video_id} ({cleaned_count}/{len(transcripts)} were LLM cleaned)")
    
    return transcripts


def clean_transcript_segments(segments, video_id: str, task_id: str = None) -> List:
    """
    Clean transcript segments using LLM postprocessing.
    
    Args:
        segments: List of transcript segments from Whisper
        video_id: Video ID for context
        task_id: Optional task ID for progress updates
    
    Returns:
        List of CleaningResult objects
    """
    try:
        from .llm_cleaning import get_llm_cleaner, BatchTextCleaner
        from .rule_based_validation import RuleBasedValidator
        
        # Get video context for better cleaning
        app = create_app()
        with app.app_context():
            from .models import Video
            video = db.session.get(Video, video_id)
            context = f"Video: {video.title}" if video and video.title else None
        
        # Initialize cleaning components
        cleaner = get_llm_cleaner()
        batch_cleaner = BatchTextCleaner(cleaner)
        validator = RuleBasedValidator()
        
        # Extract text segments
        segment_texts = [segment.text for segment in segments]
        
        logger.info(f"Starting LLM cleaning for {len(segment_texts)} transcript segments")
        
        # Batch clean segments
        cleaning_results = []
        total_segments = len(segment_texts)
        
        for i, segment_text in enumerate(segment_texts):
            if task_id and i % 5 == 0:  # Update progress every 5 segments
                progress = 85 + ((i / total_segments) * 10)  # 85-95% range
                update_task_progress(task_id, progress, 'processing', f'LLM cleaning segment {i+1}/{total_segments}')
            
            try:
                # Clean individual segment
                cleaning_result = cleaner.clean_transcript(segment_text, context)
                
                # Apply additional rule-based validation
                validation_result = validator.validate_cleaned_text(
                    segment_text, 
                    cleaning_result.cleaned_text, 
                    context
                )
                
                # Override hallucination check if validator fails
                if not validation_result.passed:
                    cleaning_result.hallucination_check_passed = False
                    cleaning_result.warnings.extend(validation_result.issues)
                    cleaning_result.confidence_score = min(cleaning_result.confidence_score, validation_result.confidence_score)
                
                cleaning_results.append(cleaning_result)
                
            except Exception as e:
                logger.error(f"Failed to clean segment {i+1}: {str(e)}")
                # Create a fallback result with original text
                from .llm_cleaning import CleaningResult
                fallback_result = CleaningResult(
                    original_text=segment_text,
                    cleaned_text=segment_text,
                    changes_made=[],
                    confidence_score=0.0,
                    processing_time=0.0,
                    hallucination_check_passed=False,
                    warnings=[f"Cleaning failed: {str(e)}"]
                )
                cleaning_results.append(fallback_result)
        
        # Log summary statistics
        successful_cleanings = sum(1 for result in cleaning_results if result.hallucination_check_passed)
        avg_confidence = sum(result.confidence_score for result in cleaning_results) / len(cleaning_results)
        total_warnings = sum(len(result.warnings) for result in cleaning_results)
        
        logger.info(f"LLM cleaning completed: {successful_cleanings}/{len(cleaning_results)} successful, "
                   f"avg confidence: {avg_confidence:.2f}, total warnings: {total_warnings}")
        
        return cleaning_results
        
    except Exception as e:
        logger.error(f"LLM cleaning pipeline failed: {str(e)}")
        # Return fallback results with original text
        from .llm_cleaning import CleaningResult
        fallback_results = []
        for segment in segments:
            fallback_result = CleaningResult(
                original_text=segment.text,
                cleaned_text=segment.text,
                changes_made=[],
                confidence_score=0.0,
                processing_time=0.0,
                hallucination_check_passed=False,
                warnings=[f"Pipeline failed: {str(e)}"]
            )
            fallback_results.append(fallback_result)
        
        return fallback_results


@celery.task(name='app.tasks.cleanup_files')
def cleanup_files(file_path: str):
    """Clean up temporary files."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to clean up file {file_path}: {str(e)}")


@celery.task(name='app.tasks.cleanup_expired_files')
def cleanup_expired_files():
    """Periodic task to clean up expired files."""
    app = create_app()
    with app.app_context():
        # Clean up files older than 1 hour
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        expired_videos = Video.query.filter(
            Video.audio_file_path.isnot(None),
            Video.updated_at < cutoff_time
        ).all()
        
        cleaned_count = 0
        for video in expired_videos:
            if video.audio_file_path and os.path.exists(video.audio_file_path):
                try:
                    os.remove(video.audio_file_path)
                    video.audio_file_path = None
                    cleaned_count += 1
                except Exception as e:
                    logger.error(f"Failed to clean up {video.audio_file_path}: {str(e)}")
        
        db.session.commit()
        logger.info(f"Cleaned up {cleaned_count} expired audio files")


@celery.task(name='app.tasks.system_health_check')
def system_health_check():
    """Periodic system health check."""
    app = create_app()
    with app.app_context():
        try:
            # Check database connectivity
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            
            # Check disk space
            audio_storage_path = app.config.get('AUDIO_STORAGE_PATH', './data/audio')
            if os.path.exists(audio_storage_path):
                stats = os.statvfs(audio_storage_path)
                free_space_gb = (stats.f_bavail * stats.f_frsize) / (1024**3)
                
                if free_space_gb < 1:  # Less than 1GB free
                    logger.warning(f"Low disk space: {free_space_gb:.2f}GB free")
            
            logger.info("System health check passed")
            
        except Exception as e:
            logger.error(f"System health check failed: {str(e)}")
            raise


@celery.task(bind=True, name='app.tasks.process_content_intelligence')
def process_content_intelligence(self, video_id: str) -> Dict[str, Any]:
    """Process content intelligence for a video: entity extraction, topic modeling, and embeddings."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get video and transcripts
            video = db.session.get(Video, video_id)
            if not video:
                raise ValueError(f"Video {video_id} not found")
            
            transcripts = Transcript.query.filter_by(video_id=video_id).order_by(Transcript.start_time).all()
            if not transcripts:
                logger.warning(f"No transcripts found for video {video_id}")
                return {'entities_count': 0, 'topics_count': 0, 'embeddings_generated': False}
            
            # Combine transcript text
            full_text = ' '.join([t.text for t in transcripts])
            
            result = {
                'entities_count': 0,
                'topics_count': 0,
                'embeddings_generated': False,
                'processing_errors': []
            }
            
            # Step 1: Entity Recognition and Linking
            try:
                entities_result = extract_and_link_entities(full_text, video_id)
                result['entities_count'] = len(entities_result.get('entities', []))
                logger.info(f"Extracted {result['entities_count']} entities for video {video_id}")
            except Exception as e:
                logger.error(f"Entity extraction failed for video {video_id}: {str(e)}")
                result['processing_errors'].append(f"Entity extraction: {str(e)}")
            
            # Step 2: Topic Modeling (break video into segments for better topic discovery)
            try:
                if len(full_text) > 500:  # Only process if sufficient content
                    # Split transcript into segments for topic modeling
                    segment_texts = []
                    segment_ids = []
                    
                    # Group transcripts into 5-minute segments or by sentence groups
                    current_segment = []
                    current_duration = 0
                    segment_count = 0
                    
                    for transcript in transcripts:
                        current_segment.append(transcript.text)
                        current_duration += (transcript.end_time - transcript.start_time) if transcript.end_time and transcript.start_time else 30
                        
                        # Create segment every 5 minutes or 10 transcript chunks
                        if current_duration >= 300 or len(current_segment) >= 10:
                            if current_segment:
                                segment_text = ' '.join(current_segment).strip()
                                if len(segment_text) > 100:  # Only include substantial segments
                                    segment_texts.append(segment_text)
                                    segment_ids.append(f"{video_id}_segment_{segment_count}")
                                    segment_count += 1
                            current_segment = []
                            current_duration = 0
                    
                    # Add remaining segment
                    if current_segment:
                        segment_text = ' '.join(current_segment).strip()
                        if len(segment_text) > 100:
                            segment_texts.append(segment_text)
                            segment_ids.append(f"{video_id}_segment_{segment_count}")
                    
                    # Process topics if we have enough segments
                    if len(segment_texts) >= 5:
                        topics_result = process_video_topics(segment_texts, segment_ids)
                        result['topics_count'] = len(topics_result.get('topics', []))
                        logger.info(f"Discovered {result['topics_count']} topics from {len(segment_texts)} segments for video {video_id}")
                    else:
                        logger.info(f"Skipping topic modeling for video {video_id} - only {len(segment_texts)} segments (need 5+)")
                else:
                    logger.info(f"Skipping topic modeling for video {video_id} - insufficient content")
            except Exception as e:
                logger.error(f"Topic modeling failed for video {video_id}: {str(e)}")
                result['processing_errors'].append(f"Topic modeling: {str(e)}")
            
            # Step 3: Vector Embeddings
            try:
                embeddings_result = generate_video_embeddings(full_text, video_id)
                result['embeddings_generated'] = embeddings_result.get('success', False)
                logger.info(f"Generated embeddings for video {video_id}")
            except Exception as e:
                logger.error(f"Embedding generation failed for video {video_id}: {str(e)}")
                result['processing_errors'].append(f"Embeddings: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Content intelligence processing failed for video {video_id}: {str(e)}")
            raise


def extract_and_link_entities(text: str, video_id: str) -> Dict[str, Any]:
    """Extract and link entities from text using Flair German NER."""
    from .entity_recognition_flair import extract_entities_from_transcript
    from .entity_linking import validate_and_link_entities
    
    # Extract entities
    extraction_result = extract_entities_from_transcript(text)
    
    # Validate and link entities
    linking_result = validate_and_link_entities(extraction_result)
    
    # Save valid entities and their mentions to database
    saved_entities = []
    saved_mentions = []
    
    for validation_result in linking_result.validated_entities:
        if validation_result.is_valid and validation_result.confidence_score > 0.6:
            canonical_name = validation_result.canonical_form or validation_result.entity.text
            entity_type = validation_result.entity_type or validation_result.entity.label
            
            # Check if entity already exists globally
            existing_entity = Entity.query.filter_by(
                canonical_name=canonical_name,
                entity_type=entity_type
            ).first()
            
            if not existing_entity:
                # Create new entity
                entity = Entity(
                    name=validation_result.entity.text,
                    canonical_name=canonical_name,
                    entity_type=entity_type,
                    confidence_score=validation_result.confidence_score,
                    external_id=validation_result.external_links.get('wikipedia') if validation_result.external_links else None,
                    description=validation_result.canonical_form  # Store canonical form as description for now
                )
                
                db.session.add(entity)
                db.session.flush()  # Get entity ID
                saved_entities.append(entity)
            else:
                entity = existing_entity
                # Update mention count
                entity.mention_count += 1
            
            # Create entity mention for this video
            mention = EntityMention(
                text=validation_result.entity.text,
                start_char=validation_result.entity.start,
                end_char=validation_result.entity.end,
                confidence=validation_result.confidence_score,
                entity_id=entity.id,
                video_id=video_id
            )
            
            db.session.add(mention)
            saved_mentions.append(mention)
    
    db.session.commit()
    
    return {
        'entities': saved_entities,
        'mentions': saved_mentions,
        'extraction_stats': {
            'total_extracted': len(extraction_result.entities),
            'total_validated': len(linking_result.validated_entities),
            'total_saved': len(saved_entities),
            'mentions_created': len(saved_mentions)
        }
    }


def process_video_topics(texts: List[str], video_ids: List[str]) -> Dict[str, Any]:
    """Process topic modeling for videos."""
    from .topic_modeling import analyze_transcript_topics
    
    # Analyze topics
    topic_result = analyze_transcript_topics(texts, video_ids)
    
    # Save topics to database
    saved_topics = []
    for topic_info in topic_result.topics:
        # Check if topic already exists
        existing_topic = Topic.query.filter_by(
            external_topic_id=topic_info.topic_id,
            model_version='bertopic_v1'
        ).first()
        
        if not existing_topic:
            topic = Topic(
                name=topic_info.name,
                description=topic_info.description,
                keywords=','.join(topic_info.keywords),
                external_topic_id=topic_info.topic_id,
                model_version='bertopic_v1',
                size=topic_info.size,
                coherence_score=topic_info.coherence_score
            )
            
            db.session.add(topic)
            saved_topics.append(topic)
    
    # Save document-topic associations
    db.session.flush()  # Ensure topics have IDs
    
    for doc_topic in topic_result.document_topics:
        if doc_topic.topic_id != -1:  # Skip outlier topic
            topic = next((t for t in saved_topics if t.external_topic_id == doc_topic.topic_id), None)
            if topic and doc_topic.document_id in video_ids:
                # This would require a video-topic association table
                # For now, we'll track this in the video metadata
                video = db.session.get(Video, doc_topic.document_id)
                if video:
                    # Store topic information in video metadata
                    if not video.metadata:
                        video.metadata = {}
                    
                    if 'topics' not in video.metadata:
                        video.metadata['topics'] = []
                    
                    video.metadata['topics'].append({
                        'topic_id': topic.id,
                        'probability': doc_topic.probability,
                        'name': topic.name
                    })
    
    db.session.commit()
    
    return {
        'topics': saved_topics,
        'processing_stats': {
            'topics_discovered': len(topic_result.topics),
            'topics_saved': len(saved_topics),
            'processing_time': topic_result.processing_time
        }
    }


def process_content_intelligence_direct(video_id: str, task_id: str) -> Dict[str, Any]:
    """Process content intelligence directly (no nested tasks) for a video: entity extraction, topic modeling, and embeddings."""
    try:
        # Get video and transcripts
        video = db.session.get(Video, video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")
        
        transcripts = Transcript.query.filter_by(video_id=video_id).order_by(Transcript.start_time).all()
        if not transcripts:
            logger.warning(f"No transcripts found for video {video_id}")
            return {'entities_count': 0, 'topics_count': 0, 'embeddings_generated': False}
        
        # Combine transcript text
        full_text = ' '.join([t.text for t in transcripts])
        
        result = {
            'entities_count': 0,
            'topics_count': 0,
            'embeddings_generated': False,
            'processing_errors': []
        }
        
        # Step 1: Entity Recognition and Linking
        try:
            update_task_progress(task_id, 87, 'processing', 'Extracting entities')
            entities_result = extract_and_link_entities(full_text, video_id)
            result['entities_count'] = len(entities_result.get('entities', []))
            logger.info(f"Extracted {result['entities_count']} entities for video {video_id}")
        except Exception as e:
            logger.error(f"Entity extraction failed for video {video_id}: {str(e)}")
            result['processing_errors'].append(f"Entity extraction: {str(e)}")
        
        # Step 2: Topic Modeling (only if we have enough content)
        try:
            if len(full_text) > 500:  # Only process if sufficient content
                update_task_progress(task_id, 92, 'processing', 'Discovering topics')
                topics_result = process_video_topics([full_text], [video_id])
                result['topics_count'] = len(topics_result.get('topics', []))
                logger.info(f"Discovered {result['topics_count']} topics for video {video_id}")
            else:
                logger.info(f"Skipping topic modeling for video {video_id} - insufficient content")
        except Exception as e:
            logger.error(f"Topic modeling failed for video {video_id}: {str(e)}")
            result['processing_errors'].append(f"Topic modeling: {str(e)}")
        
        # Step 3: Vector Embeddings
        try:
            update_task_progress(task_id, 97, 'processing', 'Generating embeddings')
            embeddings_result = generate_video_embeddings(full_text, video_id)
            result['embeddings_generated'] = embeddings_result.get('success', False)
            logger.info(f"Generated embeddings for video {video_id}")
        except Exception as e:
            logger.error(f"Embedding generation failed for video {video_id}: {str(e)}")
            result['processing_errors'].append(f"Embeddings: {str(e)}")
        
        return result
        
    except Exception as e:
        logger.error(f"Content intelligence processing failed for video {video_id}: {str(e)}")
        raise


def generate_video_embeddings(text: str, video_id: str) -> Dict[str, Any]:
    """Generate vector embeddings for video content."""
    from .vector_embeddings import generate_transcript_embeddings
    
    try:
        # Generate embeddings
        embedding_result = generate_transcript_embeddings([text], [video_id])
        
        # Save embedding to database
        embedding = Embedding(
            video_id=video_id,
            vector=embedding_result.embeddings[0].tolist(),  # Convert numpy array to list
            model_name=embedding_result.model_name,
            model_version=getattr(embedding_result, 'model_version', 'v1'),
            dimension=embedding_result.dimension,
            content_type='video',
            content_text=text[:1000]  # Store first 1000 chars for reference
        )
        
        db.session.add(embedding)
        db.session.commit()
        
        return {
            'success': True,
            'model_name': embedding_result.model_name,
            'dimension': embedding_result.dimension,
            'processing_time': embedding_result.processing_time
        }
        
    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@celery.task(name='app.tasks.batch_process_intelligence')
def batch_process_intelligence():
    """Batch process content intelligence for videos that haven't been processed."""
    app = create_app()
    
    with app.app_context():
        try:
            # Find videos that need intelligence processing
            unprocessed_videos = Video.query.filter(
                Video.processing_status == 'completed',
                ~Video.id.in_(
                    db.session.query(Entity.video_id).distinct()
                )
            ).limit(10).all()  # Process 10 at a time
            
            if not unprocessed_videos:
                logger.info("No videos need intelligence processing")
                return
            
            processed_count = 0
            for video in unprocessed_videos:
                try:
                    result = process_content_intelligence.delay(video.id).get()
                    logger.info(f"Processed intelligence for video {video.id}: {result}")
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Failed to process intelligence for video {video.id}: {str(e)}")
            
            logger.info(f"Batch processed intelligence for {processed_count} videos")
            
        except Exception as e:
            logger.error(f"Batch intelligence processing failed: {str(e)}")
            raise


@celery.task(name='app.tasks.update_topic_evolution')
def update_topic_evolution():
    """Update topic evolution tracking with recent content."""
    app = create_app()
    
    with app.app_context():
        try:
            from .topic_modeling import get_topic_manager
            
            # Get recent videos (last 7 days)
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            recent_videos = Video.query.filter(
                Video.processed_at >= cutoff_date,
                Video.processing_status == 'completed'
            ).all()
            
            if not recent_videos:
                logger.info("No recent videos for topic evolution tracking")
                return
            
            # Get topic manager and update evolution
            topic_manager = get_topic_manager()
            
            # Get trending topics
            trends = topic_manager.get_topic_trends(days_back=7)
            emerging = topic_manager.get_emerging_topics(threshold_days=7)
            declining = topic_manager.get_declining_topics()
            
            logger.info(f"Topic evolution update: {len(trends)} trends, {len(emerging)} emerging, {len(declining)} declining")
            
            # Store trend information (could be saved to database for later analysis)
            return {
                'trends_count': len(trends),
                'emerging_topics': emerging,
                'declining_topics': declining,
                'analysis_date': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Topic evolution update failed: {str(e)}")
            raise