"""
Redis fallback implementation for Windows systems.
Provides in-memory queue and result backend using Python standard library.
"""
import queue
import threading
import time
import json
import uuid
from collections import defaultdict
from typing import Any, Dict, Optional, Union
import logging

logger = logging.getLogger(__name__)


class InMemoryRedis:
    """
    In-memory Redis replacement for Windows systems.
    Provides basic Redis-like functionality for Celery broker and result backend.
    """
    
    def __init__(self):
        self._data = {}
        self._queues = defaultdict(queue.Queue)
        self._expiry = {}
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background thread for expired key cleanup."""
        def cleanup_expired():
            while True:
                try:
                    time.sleep(30)  # Check every 30 seconds
                    current_time = time.time()
                    with self._lock:
                        expired_keys = [
                            key for key, expiry in self._expiry.items() 
                            if expiry <= current_time
                        ]
                        for key in expired_keys:
                            self._data.pop(key, None)
                            self._expiry.pop(key, None)
                except Exception as e:
                    logger.error(f"Error in cleanup thread: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_expired, daemon=True)
        self._cleanup_thread.start()
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a key-value pair with optional expiration."""
        with self._lock:
            self._data[key] = value
            if ex:
                self._expiry[key] = time.time() + ex
            return True
    
    def get(self, key: str) -> Any:
        """Get value by key."""
        with self._lock:
            # Check if key has expired
            if key in self._expiry and self._expiry[key] <= time.time():
                self._data.pop(key, None)
                self._expiry.pop(key, None)
                return None
            return self._data.get(key)
    
    def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        with self._lock:
            deleted_count = 0
            for key in keys:
                if key in self._data:
                    del self._data[key]
                    deleted_count += 1
                self._expiry.pop(key, None)
            return deleted_count
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        with self._lock:
            if key in self._expiry and self._expiry[key] <= time.time():
                self._data.pop(key, None)
                self._expiry.pop(key, None)
                return False
            return key in self._data
    
    def lpush(self, queue_name: str, *values: Any) -> int:
        """Push values to the left of a list (queue)."""
        queue_obj = self._queues[queue_name]
        for value in reversed(values):  # Reverse to maintain order
            queue_obj.put(value)
        return queue_obj.qsize()
    
    def brpop(self, queue_names: Union[str, list], timeout: Optional[int] = None) -> Optional[tuple]:
        """
        Block until an element is available from one of the queues.
        Returns (queue_name, value) tuple or None if timeout.
        """
        if isinstance(queue_names, str):
            queue_names = [queue_names]
        
        start_time = time.time()
        while True:
            # Try to get from any queue
            for queue_name in queue_names:
                queue_obj = self._queues[queue_name]
                try:
                    value = queue_obj.get_nowait()
                    return (queue_name, value)
                except queue.Empty:
                    continue
            
            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return None
            
            # Small sleep to prevent busy waiting
            time.sleep(0.1)
    
    def llen(self, queue_name: str) -> int:
        """Get length of queue."""
        return self._queues[queue_name].qsize()
    
    def flushall(self) -> bool:
        """Clear all data."""
        with self._lock:
            self._data.clear()
            self._expiry.clear()
            self._queues.clear()
            return True
    
    def ping(self) -> bool:
        """Health check."""
        return True


class CeleryBrokerAdapter:
    """
    Adapter to make InMemoryRedis work as a Celery broker.
    """
    
    def __init__(self, redis_instance: InMemoryRedis):
        self.redis = redis_instance
        self._task_queue = 'celery'  # Default queue name
    
    def send_task_message(self, queue_name: str, message: Dict[str, Any]):
        """Send a task message to the queue."""
        serialized = json.dumps(message)
        self.redis.lpush(queue_name, serialized)
    
    def receive_task_message(self, queue_names: list, timeout: Optional[int] = None):
        """Receive a task message from queues."""
        result = self.redis.brpop(queue_names, timeout)
        if result:
            queue_name, serialized_message = result
            try:
                message = json.loads(serialized_message)
                return queue_name, message
            except json.JSONDecodeError as e:
                logger.error(f"Failed to deserialize message: {e}")
                return None
        return None


class CeleryResultBackend:
    """
    Result backend implementation using InMemoryRedis.
    """
    
    def __init__(self, redis_instance: InMemoryRedis):
        self.redis = redis_instance
        self._result_prefix = 'celery-task-meta-'
    
    def store_result(self, task_id: str, result: Any, state: str = 'SUCCESS', 
                    traceback: Optional[str] = None, expires: int = 3600):
        """Store task result."""
        result_data = {
            'status': state,
            'result': result,
            'traceback': traceback,
            'task_id': task_id,
            'date_done': time.time()
        }
        key = f"{self._result_prefix}{task_id}"
        self.redis.set(key, json.dumps(result_data), ex=expires)
    
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task result."""
        key = f"{self._result_prefix}{task_id}"
        serialized = self.redis.get(key)
        if serialized:
            try:
                return json.loads(serialized)
            except json.JSONDecodeError:
                return None
        return None
    
    def delete_result(self, task_id: str):
        """Delete task result."""
        key = f"{self._result_prefix}{task_id}"
        self.redis.delete(key)


# Global instances
_redis_instance = None
_broker_adapter = None
_result_backend = None


def get_redis_instance() -> InMemoryRedis:
    """Get or create the global Redis instance."""
    global _redis_instance
    if _redis_instance is None:
        _redis_instance = InMemoryRedis()
        logger.info("Created in-memory Redis fallback instance")
    return _redis_instance


def get_broker_adapter() -> CeleryBrokerAdapter:
    """Get or create the global broker adapter."""
    global _broker_adapter
    if _broker_adapter is None:
        _broker_adapter = CeleryBrokerAdapter(get_redis_instance())
    return _broker_adapter


def get_result_backend() -> CeleryResultBackend:
    """Get or create the global result backend."""
    global _result_backend
    if _result_backend is None:
        _result_backend = CeleryResultBackend(get_redis_instance())
    return _result_backend


def reset_instances():
    """Reset all global instances (for testing)."""
    global _redis_instance, _broker_adapter, _result_backend
    _redis_instance = None
    _broker_adapter = None
    _result_backend = None