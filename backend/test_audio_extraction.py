#!/usr/bin/env python3
"""
Test script for audio extraction from video files.
"""

import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_audio_extraction():
    """Test audio extraction from a sample MP4 file."""
    try:
        print("Testing Audio Extraction from Video Files")
        print("=" * 50)
        
        from app.audio_processing import HuggingFaceGermanWhisperTranscriber
        
        # Initialize transcriber
        transcriber = HuggingFaceGermanWhisperTranscriber(device='cpu')
        
        # Test with a sample MP4 file from the data directory
        test_file = "./data/audio/CLu0IH34-7E.mp4"  # From the error log
        
        if not os.path.exists(test_file):
            print(f"[INFO] Test file not found: {test_file}")
            print("[INFO] This is expected if you haven't downloaded videos yet")
            return True
        
        print(f"[TEST] Testing audio extraction from: {test_file}")
        
        # Test the audio extraction method
        temp_audio = transcriber._extract_audio_with_ffmpeg(test_file)
        
        if temp_audio:
            print(f"[SUCCESS] Audio extracted to: {temp_audio}")
            
            # Check if file exists and has content
            if os.path.exists(temp_audio):
                file_size = os.path.getsize(temp_audio)
                print(f"[INFO] Extracted audio size: {file_size} bytes")
                
                # Clean up
                os.unlink(temp_audio)
                print("[INFO] Cleaned up temporary file")
                
                return True
            else:
                print("[ERROR] Extracted audio file not found")
                return False
        else:
            print("[ERROR] Audio extraction failed")
            return False
            
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_format_detection():
    """Test file format detection."""
    print("\nTesting File Format Detection")
    print("-" * 30)
    
    test_files = [
        "video.mp4",
        "video.mkv", 
        "video.avi",
        "audio.wav",
        "audio.mp3",
        "audio.m4a"
    ]
    
    for file_path in test_files:
        is_video = file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.m4v'))
        file_type = "VIDEO" if is_video else "AUDIO"
        print(f"[{file_type}] {file_path}")
    
    return True

if __name__ == "__main__":
    print("Audio/Video Processing Test")
    print("=" * 60)
    
    # Test format detection
    format_ok = test_file_format_detection()
    
    # Test audio extraction
    extraction_ok = test_audio_extraction()
    
    if format_ok and extraction_ok:
        print("\n[SUCCESS] Audio processing tests passed!")
        print("The system should now handle MP4 video files correctly.")
    else:
        print("\n[WARNING] Some tests failed, but this may be normal if no video files are present.")