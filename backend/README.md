# Audio Summarizer Backend

This is the Flask backend for the Personal Video Intelligence Platform, implementing **Phase 1: Foundation Setup** according to the project specifications.

## ✅ Implementation Status

### Phase 1: Foundation Setup ✅
- ✅ **SQLAlchemy Database Models**: Complete schema with proper relationships
- ✅ **Flask Blueprint Architecture**: Modular API structure
- ✅ **Environment Configuration**: Flexible config management with .env support
- ✅ **Comprehensive Error Handling**: Proper exception handling and logging
- ✅ **Health Check Endpoints**: System health monitoring
- ✅ **PostgreSQL & Redis Support**: Production-ready database setup
- ✅ **Docker Configuration**: Complete containerization
- ✅ **Unit Tests**: Comprehensive test coverage for models and APIs

### Phase 2: Audio Processing Pipeline ✅
- ✅ **Celery Integration**: Robust background task processing with Redis
- ✅ **Multi-Platform Support**: YouTube, podcasts, Twitch content extraction
- ✅ **Enhanced Whisper Transcription**: GPU support, chunking, retry logic
- ✅ **Progress Tracking**: Real-time progress updates via WebSockets
- ✅ **Storage Management**: Automatic cleanup and tiered storage
- ✅ **Batch Processing**: Multiple video processing with priority queues
- ✅ **Task Management**: Cancel, retry, and monitor background jobs

### Phase 3: Content Intelligence Layer ✅
- ✅ **Domain-Specific Entity Recognition**: spaCy-based NER with custom dictionaries
- ✅ **Entity Validation & Linking**: Wikipedia/Wikidata validation with local knowledge base
- ✅ **Topic Modeling**: BERTopic for automatic topic discovery and evolution tracking
- ✅ **Vector Embeddings**: Sentence-transformers with FAISS similarity search
- ✅ **Intelligence Integration**: Automated processing pipeline in Celery tasks
- ✅ **Comprehensive Testing**: Full test coverage for all intelligence components

## 🚀 Quick Start

### Development Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Run Development Server**:
   ```bash
   python app.py
   ```

4. **Run Tests**:
   ```bash
   pytest tests/ -v
   ```

### Production Setup (Docker)

1. **Start All Services**:
   ```bash
   docker-compose up -d
   ```

This starts:
- PostgreSQL database
- Redis for caching/queues
- Flask application
- Celery worker
- YouTube session generator

## 📊 Database Schema

### Core Models:
- **Channel**: Content sources (YouTube, podcasts, etc.)
- **Video**: Individual content items
- **Transcript**: Whisper transcription segments
- **ProcessingTask**: Background job tracking
- **Topic**: AI-discovered content topics
- **Entity**: Extracted named entities
- **Embedding**: Vector representations
- **EmotionAnalysis**: Emotion detection results

## 🔌 API Endpoints

### Health & Status
- `GET /api/ping` - Simple ping test
- `GET /api/health` - System health check

### Processing
- `POST /api/process/video` - Submit video for processing (supports priority)
- `POST /api/process/batch` - Submit multiple videos for batch processing
- `GET /api/tasks/{id}` - Get task status with Celery integration
- `POST /api/tasks/{id}/cancel` - Cancel a running task
- `GET /api/tasks` - List tasks with filtering

### Data Retrieval
- `GET /api/videos` - List processed videos
- `GET /api/videos/{id}/transcripts` - Get video transcripts
- `GET /api/channels` - List channels

### Phase 3: Content Intelligence
- `GET /api/entities` - List all extracted entities with filtering
- `GET /api/videos/{id}/entities` - Get entities for a specific video
- `GET /api/topics` - List discovered topics
- `GET /api/videos/{id}/topics` - Get topics for a specific video
- `POST /api/search/semantic` - Perform semantic search using embeddings
- `GET /api/embeddings` - Get embedding information
- `GET /api/emotions` - Get emotion analysis data
- `GET /api/videos/{id}/emotions` - Get emotion analysis for a specific video
- `POST /api/videos/{id}/process-intelligence` - Trigger content intelligence processing

## 🧪 Testing

The backend includes comprehensive unit tests:

```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/test_models.py -v               # Database models
pytest tests/test_routes.py -v               # API endpoints
pytest tests/test_config.py -v               # Configuration
pytest tests/test_app.py -v                  # Application factory
pytest tests/test_entity_recognition.py -v   # Entity recognition (Phase 3)
pytest tests/test_topic_modeling.py -v       # Topic modeling (Phase 3)
pytest tests/test_vector_embeddings.py -v    # Vector embeddings (Phase 3)
pytest tests/test_entity_linking.py -v       # Entity linking (Phase 3)
```

## 🔧 Configuration

Key configuration options in `.env`:

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/audio_summarizer

# Redis
REDIS_URL=redis://localhost:6379/0

# Whisper
WHISPER_MODEL=tiny  # tiny, base, small, medium, large
WHISPER_DEVICE=cpu  # cpu, cuda

# OpenAI (for future features)
OPENAI_API_KEY=your-key-here
```

## 📈 Performance Features

- **Efficient Database Queries**: Optimized with proper indexing
- **Background Processing**: Non-blocking video processing
- **Connection Pooling**: Database connection optimization
- **Lazy Loading**: Whisper model initialization on demand
- **Error Recovery**: Automatic retry logic for failed tasks

## 🔍 Next Steps (Phase 4)

Ready for Phase 4 implementation:
- Knowledge graph construction with entity relationships
- Cross-content analysis and content similarity algorithms
- Network analysis for identifying important nodes and connections
- Spatial intelligence algorithms for content exploration

## 🛠️ Development Commands

```bash
# Database migrations (when implemented)
flask db init
flask db migrate -m "Description"
flask db upgrade

# Run development server with WebSocket support
python app.py

# Run Celery worker for background processing
celery -A celery_worker.celery worker --loglevel=info

# Run Celery beat for periodic tasks
celery -A celery_worker.celery beat --loglevel=info

# Monitor Celery tasks
celery -A celery_worker.celery flower

# Test specific endpoint
curl http://localhost:5000/api/health

# Test video processing
curl -X POST http://localhost:5000/api/process/video \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "priority": "high"}'

# Test batch processing
curl -X POST http://localhost:5000/api/process/batch \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://www.youtube.com/watch?v=1", "https://www.youtube.com/watch?v=2"]}'
```

## 🏗️ Architecture

```
audio_summarizer/backend/
├── app/
│   ├── __init__.py                # App factory
│   ├── config.py                  # Configuration classes
│   ├── models.py                  # Database models
│   ├── routes.py                  # API endpoints
│   ├── tasks.py                   # Celery background tasks
│   ├── audio_processing.py        # Enhanced Whisper transcription
│   ├── celery_app.py              # Celery configuration
│   ├── entity_recognition.py      # spaCy-based entity extraction (Phase 3)
│   ├── entity_linking.py          # Entity validation & linking (Phase 3)
│   ├── topic_modeling.py          # BERTopic topic discovery (Phase 3)
│   └── vector_embeddings.py       # Sentence-transformers & FAISS (Phase 3)
├── tests/                         # Comprehensive unit tests
│   ├── test_models.py             # Database model tests
│   ├── test_routes.py             # API endpoint tests
│   ├── test_entity_recognition.py # Entity recognition tests (Phase 3)
│   ├── test_topic_modeling.py     # Topic modeling tests (Phase 3)
│   ├── test_vector_embeddings.py  # Vector embedding tests (Phase 3)
│   └── test_entity_linking.py     # Entity linking tests (Phase 3)
├── docker-compose.yml             # Container orchestration
├── Dockerfile                     # Container definition
├── requirements.txt               # Python dependencies
└── .env.example                   # Configuration template
```

This backend provides a solid foundation for the video intelligence platform, with room to scale through the remaining phases.