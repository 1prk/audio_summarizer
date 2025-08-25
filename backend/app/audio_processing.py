"""
Enhanced audio processing module using Hugging Face German Whisper model.
Uses primeline/whisper-large-v3-turbo-german for optimized German transcription.
"""
import os
import logging
import time
import subprocess
try:
    import torch
    import torchaudio
    import librosa
    HF_AVAILABLE = True
except ImportError as e:
    print(f"Hugging Face dependencies not available: {e}")
    HF_AVAILABLE = False
    torch = None
    torchaudio = None
    librosa = None
from typing import List, Tuple, Optional, Dict, Union
from dataclasses import dataclass
import tempfile
import numpy as np

try:
    from transformers import (
        WhisperProcessor, 
        WhisperForConditionalGeneration,
        GenerationConfig,
        pipeline
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    WhisperProcessor = None
    WhisperForConditionalGeneration = None
    pipeline = None

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionSegment:
    """Data class for transcription segments."""
    text: str
    start: float
    end: float
    confidence: Optional[float] = None
    language: Optional[str] = None


@dataclass
class AudioChunk:
    """Data class for audio chunks."""
    audio_array: np.ndarray
    sample_rate: int
    start_time: float
    end_time: float
    chunk_index: int


class HuggingFaceGermanWhisperTranscriber:
    """German-optimized Whisper transcriber using Hugging Face transformers."""
    
    def __init__(self, model_name: str = "primeline/whisper-tiny-german", device: str = 'auto'):
        """
        Initialize the German Whisper transcriber.
        
        Args:
            model_name: Hugging Face model name
            device: Device to use ('cpu', 'cuda', 'auto')
        """
        self.model_name = model_name
        self.device = self._detect_device(device)
        self.processor = None
        self.model = None
        self.pipe = None
        
        # Audio processing parameters
        self.sample_rate = 16000  # Whisper's expected sample rate
        self.chunk_length_s = 30.0  # 30 seconds per chunk (Whisper's optimal length)
        self.overlap_s = 2.0  # 2 seconds overlap
        
        logger.info(f"Initializing German Whisper transcriber: model={model_name}, device={self.device}")
    
    def _detect_device(self, device: str) -> str:
        """Detect the best available device."""
        if device != 'auto':
            return device
        
        if torch.cuda.is_available():
            logger.info("CUDA available, using GPU")
            return 'cuda'
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("MPS available, using Apple Silicon GPU")
            return 'mps'
        else:
            logger.info("Using CPU")
            return 'cpu'
    
    def _load_model(self):
        """Lazy load the Whisper model and processor."""
        if self.model is None:
            logger.info(f"Loading German Whisper model: {self.model_name}")
            
            try:
                # Load processor and model
                self.processor = WhisperProcessor.from_pretrained(self.model_name)
                self.model = WhisperForConditionalGeneration.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
                    low_cpu_mem_usage=True,
                    use_safetensors=True
                )
                
                # Fix generation config for compatibility with timestamps and language
                logger.info("Updating generation config for compatibility...")
                try:
                    # Load a compatible generation config from OpenAI Whisper base model
                    compatible_config = GenerationConfig.from_pretrained("openai/whisper-base")
                    self.model.generation_config = compatible_config
                    logger.info("Generation config updated successfully")
                except Exception as config_error:
                    logger.warning(f"Could not update generation config: {config_error}")
                
                # Move model to device
                self.model = self.model.to(self.device)
                
                # Create pipeline for easier inference
                self.pipe = pipeline(
                    "automatic-speech-recognition",
                    model=self.model,
                    tokenizer=self.processor.tokenizer,
                    feature_extractor=self.processor.feature_extractor,
                    torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
                    device=self.device,
                    model_kwargs={"forced_decoder_ids": None}
                )
                
                logger.info("German Whisper model loaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to load model: {str(e)}")
                logger.info("Falling back to base whisper-large-v3")
                
                # Fallback to base model
                self.model_name = "openai/whisper-large-v3"
                self.processor = WhisperProcessor.from_pretrained(self.model_name)
                self.model = WhisperForConditionalGeneration.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
                    low_cpu_mem_usage=True
                )
                
                # The OpenAI model should already have a compatible config, but let's ensure it
                logger.info("Ensuring fallback model has compatible generation config...")
                try:
                    compatible_config = GenerationConfig.from_pretrained("openai/whisper-base")
                    self.model.generation_config = compatible_config
                    logger.info("Fallback generation config updated successfully")
                except Exception as config_error:
                    logger.warning(f"Could not update fallback generation config: {config_error}")
                
                self.model = self.model.to(self.device)
                
                self.pipe = pipeline(
                    "automatic-speech-recognition",
                    model=self.model,
                    tokenizer=self.processor.tokenizer,
                    feature_extractor=self.processor.feature_extractor,
                    torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
                    device=self.device,
                    model_kwargs={"forced_decoder_ids": None}
                )
                
                logger.info("Fallback model loaded successfully")
    
    def load_and_preprocess_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """
        Load and preprocess audio file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        try:
            # Check if this is a video file that might need special handling
            is_video_file = file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.m4v'))
            
            if is_video_file:
                logger.info(f"Video file detected: {file_path}")
                
                # Try to extract audio using ffmpeg first (if available)
                temp_audio_file = self._extract_audio_with_ffmpeg(file_path)
                if temp_audio_file:
                    try:
                        audio, sr = librosa.load(temp_audio_file, sr=self.sample_rate, mono=True)
                        # Clean up temporary file
                        os.unlink(temp_audio_file)
                        logger.info("Successfully loaded audio via ffmpeg extraction")
                    except Exception as e:
                        logger.warning(f"Failed to load extracted audio: {e}")
                        # Clean up failed temp file
                        if os.path.exists(temp_audio_file):
                            os.unlink(temp_audio_file)
                        raise
                else:
                    # ffmpeg not available or failed, try direct load with librosa
                    logger.info("ffmpeg not available, attempting direct load")
                    try:
                        audio, sr = librosa.load(file_path, sr=self.sample_rate, mono=True)
                    except Exception as e:
                        logger.error(f"Cannot load video file {file_path}: {e}")
                        logger.error("Video files require either ffmpeg for audio extraction or librosa with video codec support")
                        raise RuntimeError(f"Cannot process video file {file_path}. Please install ffmpeg or convert to audio format.")
            else:
                # Regular audio file, load directly
                audio, sr = librosa.load(file_path, sr=self.sample_rate, mono=True)
            
            # Normalize audio
            audio = librosa.util.normalize(audio)
            
            # Apply basic preprocessing
            # Remove silence from beginning and end
            audio, _ = librosa.effects.trim(audio, top_db=20)
            
            logger.info(f"Loaded audio: {len(audio)/sr:.2f}s at {sr}Hz")
            return audio, sr
            
        except Exception as e:
            logger.error(f"Error loading audio file: {str(e)}")
            raise
    
    def _extract_audio_with_ffmpeg(self, video_path: str) -> Optional[str]:
        """
        Extract audio from video file using ffmpeg.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Path to temporary audio file or None if failed
        """
        try:
            # Create temporary audio file
            temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_audio.close()
            
            # Extract audio using ffmpeg
            cmd = [
                'ffmpeg', '-i', video_path,
                '-ar', str(self.sample_rate),  # Set sample rate
                '-ac', '1',  # Mono
                '-c:a', 'pcm_s16le',  # 16-bit PCM
                '-y',  # Overwrite output file
                temp_audio.name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Audio extracted successfully: {temp_audio.name}")
                return temp_audio.name
            else:
                logger.error(f"FFmpeg audio extraction failed: {result.stderr}")
                # Clean up failed temp file
                try:
                    os.unlink(temp_audio.name)
                except:
                    pass
                return None
                
        except Exception as e:
            logger.error(f"Error extracting audio with ffmpeg: {str(e)}")
            return None
    
    def create_audio_chunks(self, audio: np.ndarray, sample_rate: int) -> List[AudioChunk]:
        """
        Split audio into chunks for processing.
        
        Args:
            audio: Audio array
            sample_rate: Sample rate
            
        Returns:
            List of AudioChunk objects
        """
        duration = len(audio) / sample_rate
        chunk_length_samples = int(self.chunk_length_s * sample_rate)
        overlap_samples = int(self.overlap_s * sample_rate)
        
        if duration <= self.chunk_length_s:
            # No need to chunk
            return [AudioChunk(audio, sample_rate, 0.0, duration, 0)]
        
        chunks = []
        chunk_index = 0
        start_sample = 0
        
        # Safety check: ensure overlap doesn't exceed chunk length
        if overlap_samples >= chunk_length_samples:
            logger.warning(f"Overlap ({self.overlap_s}s) >= chunk length ({self.chunk_length_s}s), reducing overlap")
            overlap_samples = chunk_length_samples // 2
        
        while start_sample < len(audio):
            end_sample = min(start_sample + chunk_length_samples, len(audio))
            
            # Safety check: ensure we're making progress
            if end_sample <= start_sample:
                logger.error(f"Chunking loop would not advance: start={start_sample}, end={end_sample}")
                break
            
            chunk_audio = audio[start_sample:end_sample]
            start_time = start_sample / sample_rate
            end_time = end_sample / sample_rate
            
            chunks.append(AudioChunk(
                audio_array=chunk_audio,
                sample_rate=sample_rate,
                start_time=start_time,
                end_time=end_time,
                chunk_index=chunk_index
            ))
            
            logger.info(f"Created chunk {chunk_index}: {start_time:.1f}s - {end_time:.1f}s")
            
            # Check if this is the last chunk (no more audio after this)
            if end_sample >= len(audio):
                break
                
            # Move to next chunk with overlap, but ensure we advance
            next_start = end_sample - overlap_samples
            if next_start <= start_sample:
                # If overlap would prevent progress, advance by at least half chunk
                next_start = start_sample + (chunk_length_samples // 2)
            
            start_sample = next_start
            chunk_index += 1
            
            # Safety limit to prevent infinite loops
            if chunk_index > 1000:
                logger.error(f"Too many chunks created ({chunk_index}), stopping to prevent infinite loop")
                break
        
        return chunks
    
    def transcribe_chunk_with_retry(self, chunk: AudioChunk, max_retries: int = 3) -> List[TranscriptionSegment]:
        """
        Transcribe a single chunk with retry logic.
        
        Args:
            chunk: AudioChunk to transcribe
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of TranscriptionSegment objects
        """
        self._load_model()
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Transcribing chunk {chunk.chunk_index}, attempt {attempt + 1}")
                
                # Transcribe using pipeline - simplified approach
                try:
                    # First try basic transcription without timestamps
                    result = self.pipe(chunk.audio_array)
                    logger.info(f"Transcription successful for chunk {chunk.chunk_index}")
                except Exception as pipe_error:
                    logger.error(f"Pipeline transcription failed: {pipe_error}")
                    raise pipe_error
                
                # Extract segments from result
                segments = []
                text = result.get('text', '').strip()
                if text:
                    segments.append(TranscriptionSegment(
                        text=text,
                        start=chunk.start_time,
                        end=chunk.end_time,
                        confidence=0.9,
                        language="de"
                    ))
                    logger.info(f"Extracted segment: '{text[:50]}...' for chunk {chunk.chunk_index}")
                else:
                    logger.warning(f"No text extracted for chunk {chunk.chunk_index}")
                
                logger.info(f"Successfully transcribed chunk {chunk.chunk_index}: {len(segments)} segments")
                return segments
                
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for chunk {chunk.chunk_index}: {str(e)}")
                
                if attempt < max_retries:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All attempts failed for chunk {chunk.chunk_index}")
                    return []
        
        return []
    
    def merge_overlapping_segments(self, all_segments: List[TranscriptionSegment]) -> List[TranscriptionSegment]:
        """
        Merge overlapping segments from different chunks.
        
        Args:
            all_segments: List of all transcription segments
            
        Returns:
            List of merged segments
        """
        if not all_segments:
            return []
        
        # Sort segments by start time
        sorted_segments = sorted(all_segments, key=lambda x: x.start)
        merged_segments = []
        
        for segment in sorted_segments:
            if not merged_segments:
                merged_segments.append(segment)
                continue
            
            last_segment = merged_segments[-1]
            
            # Check for overlap (within 1 second tolerance)
            if segment.start <= last_segment.end + 1.0:
                # Check for similar content to avoid duplicating overlapped speech
                if self._segments_are_similar(last_segment.text, segment.text):
                    # Skip duplicate segment
                    continue
                
                # Merge segments if end time extends beyond last segment
                if segment.end > last_segment.end:
                    # Extend the last segment
                    merged_text = last_segment.text
                    if not merged_text.endswith((' ', '.', '!', '?', ',')):
                        merged_text += ' '
                    merged_text += segment.text
                    
                    merged_segments[-1] = TranscriptionSegment(
                        text=merged_text,
                        start=last_segment.start,
                        end=segment.end,
                        confidence=min(last_segment.confidence or 0, segment.confidence or 0),
                        language=last_segment.language
                    )
                # else: segment is completely contained within last segment, skip it
            else:
                merged_segments.append(segment)
        
        return merged_segments
    
    def _segments_are_similar(self, text1: str, text2: str, threshold: float = 0.7) -> bool:
        """Check if two text segments are similar (likely overlapping speech)."""
        from difflib import SequenceMatcher
        
        # Normalize texts
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        # Calculate similarity
        similarity = SequenceMatcher(None, text1, text2).ratio()
        return similarity >= threshold
    
    def transcribe_file(self, file_path: str, progress_callback=None) -> Tuple[List[TranscriptionSegment], Dict]:
        """
        Transcribe an audio file using German-optimized Whisper.
        
        Args:
            file_path: Path to audio file
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Tuple of (segments, info_dict)
        """
        logger.info(f"Starting German Whisper transcription of: {file_path}")
        
        try:
            # Load and preprocess audio
            audio, sample_rate = self.load_and_preprocess_audio(file_path)
            
            # Create chunks
            chunks = self.create_audio_chunks(audio, sample_rate)
            logger.info(f"Created {len(chunks)} chunks for processing")
            
            # Transcribe chunks
            all_segments = []
            total_chunks = len(chunks)
            
            for i, chunk in enumerate(chunks):
                if progress_callback:
                    progress = (i / total_chunks) * 100
                    progress_callback(progress, f"Processing chunk {i+1}/{total_chunks}")
                
                chunk_segments = self.transcribe_chunk_with_retry(chunk)
                all_segments.extend(chunk_segments)
            
            # Merge overlapping segments
            merged_segments = self.merge_overlapping_segments(all_segments)
            
            # Gather info
            info = {
                'language': 'de',  # German model
                'total_segments': len(merged_segments),
                'total_chunks': total_chunks,
                'model_name': self.model_name,
                'device': self.device,
                'duration': len(audio) / sample_rate
            }
            
            logger.info(f"German Whisper transcription completed: {len(merged_segments)} segments")
            return merged_segments, info
            
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            raise


class LegacyWhisperTranscriber:
    """Legacy faster-whisper implementation as fallback."""
    
    def __init__(self, model_size: str = 'medium', device: str = 'auto', compute_type: str = 'auto'):
        """Initialize legacy transcriber."""
        logger.warning("Using legacy faster-whisper implementation as fallback")
        try:
            from faster_whisper import WhisperModel
            
            self.model_size = model_size
            self.device = device if device != 'auto' else 'cpu'
            self.compute_type = compute_type if compute_type != 'auto' else 'int8'
            
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            
        except ImportError:
            raise ImportError("faster-whisper not available and Hugging Face model failed to load")
    
    def transcribe_file(self, file_path: str, progress_callback=None) -> Tuple[List[TranscriptionSegment], Dict]:
        """Legacy transcription method."""
        logger.info(f"Using legacy transcription for: {file_path}")
        
        segments, info = self.model.transcribe(
            file_path,
            language='de',  # German
            task='transcribe',
            beam_size=5,
            best_of=5,
            temperature=0.0,
            vad_filter=True
        )
        
        # Convert to our format
        result_segments = []
        for segment in segments:
            result_segments.append(TranscriptionSegment(
                text=segment.text.strip(),
                start=segment.start,
                end=segment.end,
                confidence=getattr(segment, 'avg_logprob', None),
                language='de'
            ))
        
        info_dict = {
            'language': info.language if hasattr(info, 'language') else 'de',
            'total_segments': len(result_segments),
            'model_size': self.model_size,
            'device': self.device
        }
        
        return result_segments, info_dict


# Global transcriber instance for caching
_transcriber = None


def get_transcriber(model_size: str = 'large', device: str = 'auto') -> Union[HuggingFaceGermanWhisperTranscriber, LegacyWhisperTranscriber]:
    """
    Get or create global transcriber instance.
    
    Args:
        model_size: Model size (for legacy) or 'large' for German model
        device: Device to use ('cpu', 'cuda', 'auto')
        
    Returns:
        Transcriber instance
    """
    global _transcriber
    
    if _transcriber is None:
        # Check if ffmpeg is available for video processing
        ffmpeg_available = _check_ffmpeg_availability()
        
        if HF_AVAILABLE and TRANSFORMERS_AVAILABLE:
            if ffmpeg_available:
                try:
                    # Try to use German-optimized model (best for German content)
                    _transcriber = HuggingFaceGermanWhisperTranscriber(device=device)
                    logger.info("Using German-optimized Whisper model with ffmpeg support")
                except Exception as e:
                    logger.warning(f"Failed to load German Whisper model: {str(e)}")
                    logger.info("Falling back to legacy faster-whisper")
                    try:
                        _transcriber = LegacyWhisperTranscriber(model_size=model_size, device=device)
                    except Exception as e2:
                        logger.error(f"Failed to load legacy transcriber: {str(e2)}")
                        raise RuntimeError("No transcription backend available")
            else:
                logger.info("ffmpeg not available, using legacy faster-whisper (better video support)")
                try:
                    _transcriber = LegacyWhisperTranscriber(model_size=model_size, device=device)
                    logger.info("Legacy faster-whisper can handle video files natively")
                except Exception as e:
                    logger.warning(f"Legacy transcriber failed: {str(e)}")
                    logger.info("Attempting German model anyway (audio files only)")
                    try:
                        _transcriber = HuggingFaceGermanWhisperTranscriber(device=device)
                    except Exception as e2:
                        logger.error(f"Failed to load any transcriber: {str(e2)}")
                        raise RuntimeError("No transcription backend available")
        else:
            logger.info("Hugging Face dependencies not available, using legacy faster-whisper")
            try:
                _transcriber = LegacyWhisperTranscriber(model_size=model_size, device=device)
            except Exception as e:
                logger.error(f"Failed to load legacy transcriber: {str(e)}")
                raise RuntimeError("No transcription backend available")
    
    return _transcriber


def _check_ffmpeg_availability() -> bool:
    """Check if ffmpeg is available in the system."""
    # First, try the standard system PATH
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # On Windows, also check common installation locations
    if os.name == 'nt':  # Windows
        common_paths = [
            r'C:\ffmpeg\bin\ffmpeg.exe',
            r'C:\ffmpeg\ffmpeg.exe', 
            os.path.join(os.path.dirname(__file__), '..', '..', 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'ffmpeg', 'ffmpeg.exe'),
        ]
        
        for ffmpeg_path in common_paths:
            if os.path.exists(ffmpeg_path):
                try:
                    result = subprocess.run([ffmpeg_path, '-version'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        # Add to environment PATH for this session
                        bin_dir = os.path.dirname(ffmpeg_path)
                        if bin_dir not in os.environ.get('PATH', ''):
                            os.environ['PATH'] = f"{os.environ.get('PATH', '')};{bin_dir}"
                        return True
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                    continue
    
    return False


def clear_transcriber():
    """Clear the global transcriber instance to free memory."""
    global _transcriber
    if _transcriber is not None:
        logger.info("Clearing transcriber instance")
        _transcriber = None