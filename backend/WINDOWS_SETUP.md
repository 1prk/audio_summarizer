# Windows Setup Guide

This project now includes automatic Windows support with Redis fallback functionality.

## Automatic Platform Detection

The application automatically detects your platform and configures Redis accordingly:

- **Windows**: Uses in-memory Redis fallback (no Docker required)
- **Linux**: Uses Docker Redis containers
- **Manual Override**: Force Redis usage with environment variable

## Quick Start for Windows

### Option 1: Automatic Startup (Recommended)

```bash
# Navigate to backend directory
cd audio_summarizer/backend

# Run the Windows startup script
python start_windows.py
```

This script will:
- Detect you're on Windows
- Check if Redis is available
- Automatically use in-memory fallback if needed
- Start both Flask and Celery worker

### Option 2: Manual Setup

```bash
# Activate virtual environment (if using one)
.venv\Scripts\activate

# Set environment variables (optional)
set FLASK_ENV=development

# Start Flask app
python app.py

# In another terminal, start Celery worker
python -m celery -A app.celery_app.celery worker --pool=solo --loglevel=info
```

## Configuration Details

### Automatic Configuration (Windows)
- **Redis URL**: `memory://` (in-memory fallback)
- **Celery Broker**: `memory://` (in-memory fallback)
- **Result Backend**: `cache+memory://` (in-memory fallback)

### Force Redis Usage
If you have Redis installed on Windows and want to use it:

```bash
# Set environment variable to force Redis usage
set FORCE_REDIS=1
python start_windows.py
```

### Linux/Docker Configuration
- **Redis URL**: `redis://localhost:6379/0`
- **Celery Broker**: `redis://localhost:6379/0`
- **Result Backend**: `redis://localhost:6379/0`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FORCE_REDIS` | Force Redis usage even on Windows | Not set |
| `FLASK_ENV` | Flask environment | `development` |
| `START_MODE` | Startup mode (both/flask/celery) | `both` |
| `REDIS_URL` | Redis connection URL | Auto-detected |
| `CELERY_BROKER_URL` | Celery broker URL | Auto-detected |
| `CELERY_RESULT_BACKEND` | Celery result backend URL | Auto-detected |

## Features of Windows Fallback

The in-memory Redis fallback provides:

### Core Redis Operations
- Key-value storage with expiration
- Queue operations (lpush, brpop)
- Basic data types support
- Automatic cleanup of expired keys

### Celery Integration
- Task queuing and execution
- Result storage and retrieval
- Worker management
- Task routing support

### Limitations
- **In-memory only**: Data is lost when application restarts
- **Single process**: No distributed workers
- **No persistence**: No data survives crashes
- **Limited scalability**: Suitable for development/testing

## Startup Modes

You can control what components start:

```bash
# Start both Flask and Celery (default)
python start_windows.py
# or
set START_MODE=both && python start_windows.py

# Start only Flask app
set START_MODE=flask && python start_windows.py

# Start only Celery worker
set START_MODE=celery && python start_windows.py
```

## Testing the Setup

### Verify Platform Detection
```bash
python -c "from app.config import config; c = config['default']; print(f'Windows: {c.IS_WINDOWS}, Fallback: {c.USE_REDIS_FALLBACK}')"
```

### Test Redis Fallback
```bash
python -c "from app.redis_fallback import get_redis_instance; r = get_redis_instance(); r.set('test', 'value'); print('Test:', r.get('test'))"
```

### Check Celery Configuration
```bash
python -c "from app.celery_app import celery; print('Broker:', celery.conf.broker_url)"
```

## Troubleshooting

### Common Issues

1. **Module Not Found Errors**
   ```bash
   # Make sure you're in the right directory
   cd audio_summarizer/backend
   
   # Check Python path
   python -c "import sys; print(sys.path)"
   ```

2. **Virtual Environment Issues**
   ```bash
   # Activate virtual environment if needed
   .venv\Scripts\activate
   
   # Or use full path to Python
   .venv\Scripts\python start_windows.py
   ```

3. **Port Already in Use**
   ```bash
   # Check what's using port 5000
   netstat -ano | findstr :5000
   
   # Kill the process or use different port
   set FLASK_RUN_PORT=5001
   ```

4. **Celery Worker Issues on Windows**
   - Use `--pool=solo` for Windows compatibility
   - Avoid `--pool=prefork` on Windows
   - Check for firewall blocking localhost connections

### Performance Considerations

- **Development**: In-memory fallback is perfect
- **Testing**: Suitable for unit/integration tests
- **Production**: Use proper Redis server
- **Heavy loads**: Switch to Redis for better performance

### Migration from Fallback to Redis

To switch from in-memory fallback to Redis:

1. Install Redis on Windows or use Docker
2. Set `FORCE_REDIS=1` environment variable
3. Update Redis URL if using custom configuration
4. Restart the application

## Docker Alternative for Windows

If you prefer using Docker on Windows:

```bash
# Install Docker Desktop for Windows
# Then use the standard docker-compose setup
docker-compose up -d
```

This will run Redis in containers even on Windows.