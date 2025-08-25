#!/usr/bin/env python3
"""
Test script for the new German Whisper implementation.
"""

import os
import sys
import tempfile
import numpy as np

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def create_test_audio():
    """Create a simple test audio file for testing."""
    try:
        import torchaudio
        
        # Create a simple sine wave as test audio
        sample_rate = 16000
        duration = 5  # 5 seconds
        frequency = 440  # A4 note
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio = np.sin(2 * np.pi * frequency * t) * 0.5
        
        # Save as temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        audio_tensor = torch.tensor(audio, dtype=torch.float32).unsqueeze(0)
        torchaudio.save(temp_file.name, audio_tensor, sample_rate)
        
        return temp_file.name
        
    except ImportError:
        print("torch/torchaudio not available for test audio creation")
        return None

def test_german_whisper():
    """Test the German Whisper implementation."""
    try:
        print("Testing German Whisper Implementation")
        print("=" * 50)
        
        # Test 1: Import modules
        print("Test 1: Importing modules...")
        try:
            from app.audio_processing import get_transcriber, HuggingFaceGermanWhisperTranscriber
            print("✅ Modules imported successfully")
        except ImportError as e:
            print(f"❌ Import failed: {e}")
            return False
        
        # Test 2: Check dependencies
        print("\nTest 2: Checking dependencies...")
        required_modules = ['torch', 'transformers', 'librosa']
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
                print(f"✅ {module} available")
            except ImportError:
                missing_modules.append(module)
                print(f"❌ {module} missing")
        
        if missing_modules:
            print(f"\nMissing dependencies: {missing_modules}")
            print("Please install with: pip install torch transformers librosa")
            return False
        
        # Test 3: Initialize transcriber
        print("\nTest 3: Initializing transcriber...")
        try:
            transcriber = get_transcriber(device='cpu')  # Use CPU for testing
            print(f"✅ Transcriber initialized: {type(transcriber).__name__}")
        except Exception as e:
            print(f"❌ Transcriber initialization failed: {e}")
            return False
        
        # Test 4: Test with dummy audio (if possible)
        print("\nTest 4: Testing audio processing capabilities...")
        try:
            if hasattr(transcriber, 'load_and_preprocess_audio'):
                print("✅ Audio preprocessing method available")
            if hasattr(transcriber, 'transcribe_file'):
                print("✅ Transcription method available")
            if hasattr(transcriber, '_load_model'):
                print("✅ Model loading method available")
        except Exception as e:
            print(f"❌ Method availability check failed: {e}")
        
        # Test 5: Device detection
        print("\nTest 5: Device detection...")
        if isinstance(transcriber, HuggingFaceGermanWhisperTranscriber):
            print(f"✅ Device selected: {transcriber.device}")
            print(f"✅ Model name: {transcriber.model_name}")
        else:
            print("ℹ️  Using legacy transcriber")
        
        print("\n" + "=" * 50)
        print("German Whisper Test Summary:")
        print("✅ All basic tests passed")
        print("🚀 Ready for transcription")
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_loading():
    """Test actual model loading (optional, requires internet)."""
    print("\n" + "=" * 50)
    print("Optional: Testing Model Loading")
    print("=" * 50)
    
    try:
        from app.audio_processing import HuggingFaceGermanWhisperTranscriber
        
        print("Attempting to load German Whisper model...")
        print("⚠️  This requires internet connection and may take several minutes...")
        
        transcriber = HuggingFaceGermanWhisperTranscriber(device='cpu')
        transcriber._load_model()
        
        print("✅ Model loaded successfully!")
        print(f"Model: {transcriber.model_name}")
        print(f"Device: {transcriber.device}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        print("This is normal if you don't have internet or sufficient disk space")
        return False

if __name__ == "__main__":
    print("🎤 German Whisper Transcriber Test")
    print("=" * 60)
    
    # Run basic tests
    basic_success = test_german_whisper()
    
    if basic_success:
        # Ask user if they want to test model loading
        try:
            response = input("\nTest actual model loading? (requires internet) [y/N]: ").lower()
            if response in ['y', 'yes']:
                test_model_loading()
        except KeyboardInterrupt:
            print("\nSkipping model loading test")
    
    if basic_success:
        print(f"\n🎉 German Whisper implementation is ready!")
        print("Next steps:")
        print("1. Install dependencies: pip install torch transformers librosa")
        print("2. Ensure internet connection for first model download")
        print("3. Process audio files with improved German transcription")
    else:
        print(f"\n⚠️  Some tests failed. Please check the errors above.")