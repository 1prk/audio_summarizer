# Audio Summarizer API Documentation

A comprehensive guide to the Personal Video Intelligence Platform API, demonstrated with real examples using the Rick Astley "Never Gonna Give You Up" video.

**Base URL**: `http://localhost:5000`  
**API Version**: 1.0.0  
**Content-Type**: `application/json`

## 📋 Table of Contents

1. [Health & Status Endpoints](#health--status-endpoints)
2. [Video Processing Endpoints](#video-processing-endpoints)
3. [Task Management Endpoints](#task-management-endpoints)
4. [Data Retrieval Endpoints](#data-retrieval-endpoints)
5. [Error Handling](#error-handling)
6. [Rate Limiting & Best Practices](#rate-limiting--best-practices)

---

## 🏥 Health & Status Endpoints

### GET /api/ping
Simple ping endpoint for basic connectivity testing.

**Response (200 OK):**
```json
{
  "message": "pong",
  "timestamp": "2025-01-17T15:30:45.123456"
}
```

### GET /api/health
Comprehensive system health check including database connectivity.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-17T15:30:45.123456",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "whisper": "healthy"
  }
}
```

**Response (503 Service Unavailable)** when unhealthy:
```json
{
  "status": "unhealthy",
  "timestamp": "2025-01-17T15:30:45.123456",
  "version": "1.0.0",
  "services": {
    "database": "unhealthy",
    "whisper": "healthy"
  }
}
```

---

## 🎬 Video Processing Endpoints

### POST /api/process/video
Submit a single video for transcription and analysis. Supports priority levels and deduplication.

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "priority": "normal"
}
```

**Parameters:**
- `url` (string, required): Video URL (YouTube, podcast, Twitch)
- `priority` (string, optional): Processing priority - "low", "normal", "high" (default: "normal")

**Response (202 Accepted)** for new video:
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "queued",
  "message": "Video processing started",
  "celery_task_id": "12345678-9abc-def0-1234-567890abcdef"
}
```

**Response (200 OK)** for already processed video:
```json
{
  "video_id": "3c5669c0-04df-4cf5-ae4e-cd85641dfab6",
  "message": "Video already processed",
  "status": "completed"
}
```

**Response (200 OK)** for video currently processing:
```json
{
  "task_id": "existing-task-id",
  "message": "Video is already being processed",
  "status": "processing"
}
```

### POST /api/process/direct
Process a video directly without Celery queue (legacy style, useful for debugging).

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Response (200 OK):**
```json
{
  "video_id": "3c5669c0-04df-4cf5-ae4e-cd85641dfab6",
  "title": "Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)",
  "transcript_segments": 56,
  "status": "completed",
  "message": "Video processed successfully"
}
```

### POST /api/process/batch
Submit multiple videos for batch processing (maximum 50 URLs per batch).

**Request Body:**
```json
{
  "urls": [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=9bZkp7q19f0",
    "https://www.youtube.com/watch?v=astISOttCQ0"
  ]
}
```

**Response (202 Accepted):**
```json
{
  "batch_id": "b7d5c3e9-1a2b-4c5d-6e7f-890123456789",
  "tasks": [
    {
      "task_id": "task-1-id",
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "celery_task_id": "celery-1-id"
    },
    {
      "task_id": "task-2-id", 
      "url": "https://www.youtube.com/watch?v=9bZkp7q19f0",
      "celery_task_id": "celery-2-id"
    }
  ],
  "message": "Batch processing started for 2 videos"
}
```

---

## ⚙️ Task Management Endpoints

### GET /api/tasks/{task_id}
Get detailed status of a processing task, including Celery integration.

**Example Request:** `GET /api/tasks/a1b2c3d4-e5f6-7890-abcd-ef1234567890`

**Response (200 OK)** for completed task:
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "progress": 100.0,
  "task_type": "transcription",
  "created_at": "2025-01-17T15:25:30.123456",
  "started_at": "2025-01-17T15:25:35.123456",
  "completed_at": "2025-01-17T15:27:45.123456",
  "celery": {
    "task_id": "12345678-9abc-def0-1234-567890abcdef",
    "state": "SUCCESS",
    "info": {}
  },
  "result": {
    "video_id": "3c5669c0-04df-4cf5-ae4e-cd85641dfab6",
    "transcript_count": 56,
    "status": "completed"
  },
  "video": {
    "id": "3c5669c0-04df-4cf5-ae4e-cd85641dfab6",
    "title": "Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)",
    "external_id": "dQw4w9WgXcQ",
    "processing_status": "completed",
    "platform": "youtube"
  }
}
```

**Response (200 OK)** for task in progress:
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "progress": 65.5,
  "task_type": "transcription",
  "created_at": "2025-01-17T15:25:30.123456",
  "started_at": "2025-01-17T15:25:35.123456",
  "completed_at": null,
  "celery": {
    "task_id": "12345678-9abc-def0-1234-567890abcdef",
    "state": "PROGRESS",
    "info": {
      "progress": 65.5,
      "message": "Transcribing audio"
    }
  },
  "current_step": "Transcribing audio"
}
```

### POST /api/tasks/{task_id}/cancel
Cancel a running or queued task.

**Example Request:** `POST /api/tasks/a1b2c3d4-e5f6-7890-abcd-ef1234567890/cancel`

**Response (200 OK):**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "cancelled",
  "message": "Task cancelled successfully"
}
```

**Error Response (400 Bad Request)** for non-cancellable task:
```json
{
  "error": "Task cannot be cancelled"
}
```

### GET /api/tasks
List tasks with filtering and pagination support.

**Query Parameters:**
- `page` (int, optional): Page number (default: 1)
- `per_page` (int, optional): Items per page (max: 100, default: 20)
- `status` (string, optional): Filter by status - "queued", "processing", "completed", "failed", "cancelled"
- `task_type` (string, optional): Filter by type - "transcription"

**Example Request:** `GET /api/tasks?status=completed&page=1&per_page=5`

**Response (200 OK):**
```json
{
  "tasks": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "task_type": "transcription",
      "status": "completed",
      "progress": 100.0,
      "created_at": "2025-01-17T15:25:30.123456",
      "started_at": "2025-01-17T15:25:35.123456",
      "completed_at": "2025-01-17T15:27:45.123456",
      "input_data": {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "priority": "normal",
        "celery_task_id": "12345678-9abc-def0-1234-567890abcdef"
      },
      "video_id": "3c5669c0-04df-4cf5-ae4e-cd85641dfab6"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 5,
    "total": 1,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

---

## 📊 Data Retrieval Endpoints

### GET /api/videos
List processed videos with filtering and pagination.

**Query Parameters:**
- `page` (int, optional): Page number (default: 1)
- `per_page` (int, optional): Items per page (max: 100, default: 20)
- `status` (string, optional): Filter by processing status - "pending", "processing", "completed", "failed"

**Example Request:** `GET /api/videos?status=completed&page=1&per_page=5`

**Response (200 OK):**
```json
{
  "videos": [
    {
      "id": "3c5669c0-04df-4cf5-ae4e-cd85641dfab6",
      "title": "Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)",
      "external_id": "dQw4w9WgXcQ",
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "duration": 213,
      "processing_status": "completed",
      "created_at": "2025-01-17T15:25:30.123456",
      "processed_at": "2025-01-17T15:27:45.123456",
      "channel": {
        "id": "ch-rick-astley-id",
        "name": "Rick Astley",
        "platform": "youtube"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 5,
    "total": 1,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

### GET /api/videos/{video_id}/transcripts
Get all transcript segments for a specific video, ordered by start time.

**Example Request:** `GET /api/videos/3c5669c0-04df-4cf5-ae4e-cd85641dfab6/transcripts`

**Response (200 OK):**
```json
{
  "video_id": "3c5669c0-04df-4cf5-ae4e-cd85641dfab6",
  "video_title": "Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)",
  "transcripts": [
    {
      "id": "transcript-1-id",
      "text": "Let's go!",
      "start_time": 0.0,
      "end_time": 17.02,
      "confidence": 0.95,
      "speaker": null
    },
    {
      "id": "transcript-2-id", 
      "text": "They're no strangers to love",
      "start_time": 17.02,
      "end_time": 22.02,
      "confidence": 0.98,
      "speaker": null
    },
    {
      "id": "transcript-3-id",
      "text": "You know the rules, and so do I",
      "start_time": 22.02,
      "end_time": 27.02,
      "confidence": 0.97,
      "speaker": null
    }
  ]
}
```

### GET /api/channels
List all active channels in the system.

**Response (200 OK):**
```json
{
  "channels": [
    {
      "id": "ch-rick-astley-id",
      "name": "Rick Astley",
      "platform": "youtube",
      "external_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
      "url": "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
      "video_count": 1,
      "created_at": "2025-01-17T15:25:30.123456"
    }
  ]
}
```

---

## ❌ Error Handling

The API uses standard HTTP status codes and returns consistent error responses.

### Common Error Formats

**400 Bad Request:**
```json
{
  "error": "URL is required in request body"
}
```

**404 Not Found:**
```json
{
  "error": "Video not found"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal server error"
}
```

### Processing Errors
When video processing fails, the task status will show:

```json
{
  "task_id": "failed-task-id",
  "status": "failed",
  "progress": 0.0,
  "error": "Failed to extract metadata: Video is private"
}
```

### Common Error Scenarios

1. **Invalid URL Format**: `"Invalid URL format"`
2. **Video Not Available**: `"Failed to extract metadata: Video is private"`
3. **Audio Download Failed**: `"No audio file found for video_id"`
4. **Transcription Failed**: `"Whisper transcription failed"`
5. **Task Not Found**: `"Task not found"`
6. **Batch Size Exceeded**: `"Maximum 50 URLs per batch"`

---

## 🔧 Rate Limiting & Best Practices

### Request Limits
- **Batch Processing**: Maximum 50 URLs per request
- **Pagination**: Maximum 100 items per page
- **Concurrent Processing**: Limited by system resources

### Best Practices

1. **Check for Existing Videos**: The API automatically handles deduplication, but you can check `/api/videos` first to avoid unnecessary requests.

2. **Monitor Task Progress**: Use `/api/tasks/{task_id}` to monitor long-running operations instead of polling.

3. **Use Appropriate Priority**: 
   - `high`: Time-sensitive content
   - `normal`: Regular processing (default)
   - `low`: Batch/background processing

4. **Handle Errors Gracefully**: Always check HTTP status codes and error messages.

5. **Pagination**: Use pagination for large result sets to avoid timeouts.

### Example Workflows

#### Single Video Processing
```bash
# 1. Submit video for processing
curl -X POST http://localhost:5000/api/process/video \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "priority": "normal"}'

# 2. Monitor progress
curl http://localhost:5000/api/tasks/{task_id}

# 3. Retrieve transcripts when completed
curl http://localhost:5000/api/videos/{video_id}/transcripts
```

#### Batch Processing
```bash
# 1. Submit batch
curl -X POST http://localhost:5000/api/process/batch \
  -H "Content-Type: application/json" \
  -d '{"urls": ["url1", "url2", "url3"]}'

# 2. Monitor all tasks
curl "http://localhost:5000/api/tasks?status=processing"

# 3. List completed videos
curl "http://localhost:5000/api/videos?status=completed"
```

---

## 📝 Example Integration

Here's a complete Python example demonstrating API usage:

```python
import requests
import time
import json

BASE_URL = "http://localhost:5000"

def process_video(url, priority="normal"):
    """Submit a video for processing and wait for completion."""
    
    # Submit video
    response = requests.post(f"{BASE_URL}/api/process/video", 
                           json={"url": url, "priority": priority})
    
    if response.status_code == 200:
        # Video already processed
        return response.json()["video_id"]
    elif response.status_code == 202:
        # New processing task
        task_id = response.json()["task_id"]
        
        # Monitor progress
        while True:
            task_response = requests.get(f"{BASE_URL}/api/tasks/{task_id}")
            task_data = task_response.json()
            
            print(f"Progress: {task_data['progress']:.1f}%")
            
            if task_data["status"] == "completed":
                return task_data["video"]["id"]
            elif task_data["status"] == "failed":
                raise Exception(f"Processing failed: {task_data.get('error')}")
                
            time.sleep(5)  # Check every 5 seconds
    else:
        raise Exception(f"Failed to submit video: {response.text}")

def get_transcripts(video_id):
    """Get transcripts for a processed video."""
    response = requests.get(f"{BASE_URL}/api/videos/{video_id}/transcripts")
    return response.json()["transcripts"]

# Example usage
if __name__ == "__main__":
    # Process Rick Roll video
    video_id = process_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    print(f"Video processed: {video_id}")
    
    # Get transcripts
    transcripts = get_transcripts(video_id)
    print(f"Found {len(transcripts)} transcript segments")
    
    # Print first few segments
    for i, segment in enumerate(transcripts[:3]):
        print(f"{segment['start_time']:.1f}s: {segment['text']}")
```

---

## 🚀 Getting Started

1. **Health Check**: `GET /api/ping` to verify API connectivity
2. **Process Test Video**: Use the Rick Roll example URL for testing
3. **Monitor Progress**: Check task status until completion
4. **Explore Data**: Browse videos, channels, and transcripts
5. **Integrate**: Use the Python example as a starting point

For more advanced features like content intelligence, topic modeling, and vector embeddings, see the backend README for Phase 3+ capabilities.