#!/usr/bin/env python3
"""
Automatic FFmpeg setup for German Whisper support.
"""

import os
import sys
import urllib.request
import zipfile
import tempfile
import subprocess
from pathlib import Path

def download_ffmpeg():
    """Download and extract FFmpeg."""
    print("🔽 Downloading FFmpeg...")
    
    # FFmpeg download URL (Windows essentials build)
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    
    # Create ffmpeg directory
    ffmpeg_dir = Path("C:/ffmpeg")
    ffmpeg_dir.mkdir(exist_ok=True)
    
    try:
        # Download to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            print("Downloading from:", ffmpeg_url)
            urllib.request.urlretrieve(ffmpeg_url, tmp_file.name)
            
            print("📦 Extracting FFmpeg...")
            
            # Extract zip file
            with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                # Find the ffmpeg folder in the zip
                for member in zip_ref.namelist():
                    if member.endswith('bin/ffmpeg.exe'):
                        # Extract the bin directory contents
                        base_path = member.rsplit('/', 2)[0]  # Get base folder
                        for bin_member in zip_ref.namelist():
                            if bin_member.startswith(base_path + '/bin/'):
                                # Extract to C:\ffmpeg\bin\
                                target_path = ffmpeg_dir / bin_member.split('/')[-1]
                                with zip_ref.open(bin_member) as source, open(target_path, 'wb') as target:
                                    target.write(source.read())
                        break
            
            # Clean up temporary file
            os.unlink(tmp_file.name)
            
            # Verify extraction
            ffmpeg_exe = ffmpeg_dir / "bin" / "ffmpeg.exe"
            if ffmpeg_exe.exists():
                print(f"✅ FFmpeg extracted to: {ffmpeg_exe}")
                return True
            else:
                print("❌ FFmpeg extraction failed")
                return False
                
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

def add_to_path():
    """Add FFmpeg to system PATH."""
    try:
        ffmpeg_bin = "C:\\ffmpeg\\bin"
        
        # Check current PATH
        current_path = os.environ.get('PATH', '')
        if ffmpeg_bin in current_path:
            print("✅ FFmpeg already in PATH")
            return True
        
        print("🔧 Adding FFmpeg to system PATH...")
        
        # Try to add to system PATH (requires admin rights)
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               "System\\CurrentControlSet\\Control\\Session Manager\\Environment",
                               0, winreg.KEY_ALL_ACCESS) as key:
                current_path = winreg.QueryValueEx(key, "PATH")[0]
                if ffmpeg_bin not in current_path:
                    new_path = f"{current_path};{ffmpeg_bin}"
                    winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
                    print("✅ Added to system PATH (restart required)")
                
        except PermissionError:
            print("⚠️  Admin rights needed for system PATH. Adding to user PATH instead...")
            
            # Fallback: add to user PATH
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                try:
                    current_path = winreg.QueryValueEx(key, "PATH")[0]
                except FileNotFoundError:
                    current_path = ""
                
                if ffmpeg_bin not in current_path:
                    new_path = f"{current_path};{ffmpeg_bin}" if current_path else ffmpeg_bin
                    winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
                    print("✅ Added to user PATH")
        
        # Update current session PATH
        os.environ['PATH'] = f"{os.environ.get('PATH', '')};{ffmpeg_bin}"
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to add to PATH: {e}")
        return False

def test_ffmpeg():
    """Test FFmpeg installation."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg working: {version_line}")
            return True
        else:
            print("❌ FFmpeg test failed")
            return False
    except Exception as e:
        print(f"❌ FFmpeg not accessible: {e}")
        return False

def test_transcriber():
    """Test German Whisper transcriber."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
        
        from app.audio_processing import get_transcriber, _check_ffmpeg_availability
        
        ffmpeg_ok = _check_ffmpeg_availability()
        print(f"FFmpeg detection: {ffmpeg_ok}")
        
        transcriber = get_transcriber(device='cpu')
        transcriber_type = type(transcriber).__name__
        print(f"Selected transcriber: {transcriber_type}")
        
        if transcriber_type == "HuggingFaceGermanWhisperTranscriber":
            print("🎯 SUCCESS: German Whisper model ready for video processing!")
            return True
        else:
            print("ℹ️  Using legacy transcriber (still works, but less German optimization)")
            return True
            
    except Exception as e:
        print(f"❌ Transcriber test failed: {e}")
        return False

def main():
    """Main setup function."""
    print("🎬 FFmpeg Setup for German Whisper")
    print("=" * 50)
    
    # Check if FFmpeg is already available
    if test_ffmpeg():
        print("FFmpeg already installed and working!")
        test_transcriber()
        return
    
    # Check if FFmpeg exists but not in PATH
    ffmpeg_exe = Path("C:/ffmpeg/bin/ffmpeg.exe")
    if ffmpeg_exe.exists():
        print("FFmpeg found but not in PATH. Fixing PATH...")
        add_to_path()
        if test_ffmpeg():
            test_transcriber()
            return
    
    # Download and install FFmpeg
    print("FFmpeg not found. Downloading...")
    
    if download_ffmpeg():
        if add_to_path():
            if test_ffmpeg():
                print("\n🎉 Installation completed successfully!")
                test_transcriber()
            else:
                print("\n⚠️  Installation completed but FFmpeg not accessible.")
                print("Please restart your terminal or reboot Windows.")
        else:
            print("\n⚠️  FFmpeg downloaded but PATH setup failed.")
            print("Please manually add C:\\ffmpeg\\bin to your PATH.")
    else:
        print("\n❌ Installation failed.")
        print("Please install FFmpeg manually:")
        print("1. Download: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip")
        print("2. Extract to C:\\ffmpeg")
        print("3. Add C:\\ffmpeg\\bin to PATH")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please try manual installation instead.")