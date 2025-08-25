@echo off
echo Installing FFmpeg for German Whisper Support
echo ============================================
echo.

REM Create ffmpeg directory
if not exist "C:\ffmpeg" mkdir "C:\ffmpeg"

echo Step 1: Download FFmpeg
echo -----------------------
echo Please download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
echo Save it to your Downloads folder
echo.
pause

echo Step 2: Extract FFmpeg
echo ----------------------
echo Please extract the downloaded zip file to C:\ffmpeg
echo You should have C:\ffmpeg\bin\ffmpeg.exe after extraction
echo.
pause

REM Add to PATH
echo Step 3: Adding FFmpeg to PATH
echo -----------------------------
setx PATH "%PATH%;C:\ffmpeg\bin" /M
echo Added C:\ffmpeg\bin to system PATH

echo.
echo Step 4: Verify Installation
echo ---------------------------
echo Please close this window and open a new Command Prompt or PowerShell
echo Then test with: ffmpeg -version
echo.
echo If successful, the German Whisper model will be able to process video files!
echo.
pause