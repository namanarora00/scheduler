import time
from redis import Redis
from typing import Optional

class RedisLock:
    def __init__(self, redis_client: Redis, lock_key: str, expire_seconds: int = 30):
        """
        Initialize a Redis-based distributed lock
        :param redis_client: Redis client instance
        :param lock_key: Unique key for the lock
        :param expire_seconds: Lock expiry time in seconds (default: 30)
        """
        self.redis = redis_client
        self.lock_key = f"lock:{lock_key}"
        self.expire_seconds = expire_seconds
        self._owner = None

    def acquire(self, timeout: int = 10, retry_delay: float = 0.5) -> bool:
        """
        Acquire the lock with timeout
        :param timeout: Maximum time to wait for lock in seconds
        :param retry_delay: Time to wait between retries in seconds
        :return: True if lock acquired, False otherwise
        """
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            # Try to set the lock key with expiry
            success = self.redis.set(
                self.lock_key,
                "1",
                ex=self.expire_seconds,
                nx=True  # Only set if key doesn't exist
            )
            
            if success:
                self._owner = True
                return True
                
            # Wait before retrying
            time.sleep(retry_delay)
            
        return False

    def release(self) -> bool:
        """
        Release the lock if owned
        :return: True if lock was released, False if not owned
        """
        if not self._owner:
            return False
            
        self.redis.delete(self.lock_key)
        self._owner = False
        return True

    def __enter__(self):
        """Context manager entry"""
        success = self.acquire()
        if not success:
            raise TimeoutError(f"Could not acquire lock for {self.lock_key}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release() 