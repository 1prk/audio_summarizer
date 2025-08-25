# Quick FFmpeg Installation Guide

## Manual Installation (Recommended)

### Step 1: Download FFmpeg
1. Go to: https://www.gyan.dev/ffmpeg/builds/
2. Download: **ffmpeg-release-essentials.zip** (about 70MB)
3. Save to your Downloads folder

### Step 2: Extract and Install
1. Extract the ZIP file to `C:\ffmpeg`
2. You should have: `C:\ffmpeg\bin\ffmpeg.exe`

### Step 3: Add to PATH
Run this in **PowerShell as Administrator**:
```powershell
$env:PATH += ";C:\ffmpeg\bin"
[Environment]::SetEnvironmentVariable("PATH", $env:PATH, [EnvironmentVariableTarget]::Machine)
```

### Step 4: Verify Installation
Open a **new** Command Prompt and run:
```bash
ffmpeg -version
```

You should see ffmpeg version information.

## Alternative: Portable Installation

If you can't modify system PATH:

1. Download and extract ffmpeg to your project folder:
   `C:\Users\Porojkow\Documents\Sonstiges\audio_summarizer\ffmpeg\`

2. The system will automatically find it in the project directory.

## Test After Installation

Run this to test:
```bash
cd C:\Users\Porojkow\Documents\Sonstiges\audio_summarizer\audio_summarizer\backend
python -c "
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath('.')), 'app'))
from app.audio_processing import _check_ffmpeg_availability, get_transcriber
print('FFmpeg available:', _check_ffmpeg_availability())
transcriber = get_transcriber()
print('Transcriber:', type(transcriber).__name__)
"
```

## Expected Result

After successful installation:
- ✅ **FFmpeg available: True**
- ✅ **Transcriber: HuggingFaceGermanWhisperTranscriber**
- ✅ **Ready to process MP4 video files with German optimization!**

## If Installation Fails

The system will automatically fall back to:
- **Legacy faster-whisper** (can handle MP4 files natively)
- Still works, but without German-specific optimizations

## Benefits with FFmpeg

- 🎯 **German-optimized Whisper model** for better accuracy
- 🎬 **Full video format support** (MP4, AVI, MKV, MOV)
- 🔊 **Enhanced audio preprocessing** 
- ⚡ **Better performance** on German content