import os
from redis import Redis
from rq import Queue
from typing import Dict, Any

class QueueService:
    _instance = None
    _redis = None
    _queue = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize Redis connection and queue"""
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        
        self._redis = Redis(host=redis_host, port=redis_port)
        self._queue = Queue('deployments', connection=self._redis)

    def enqueue_deployment(self, deployment_id: int):
        """
        Add a deployment to the queue.
        :param deployment_id: ID of the deployment
        """
        
        job_id = f"deployment:{deployment_id}"
        
        self._queue.enqueue(
            'worker.process_deployment',
            deployment_id,
            job_id=job_id
        )

    def get_queue_status(self) -> Dict[str, int]:
        """Get current queue statistics"""
        return {
            'queued': len(self._queue),
            'started': len(self._queue.started_job_registry),
            'finished': len(self._queue.finished_job_registry),
            'failed': len(self._queue.failed_job_registry),
        }

    def get_deployment_status(self, deployment_id: int) -> str:
        """
        Get the current status of a deployment in the queue
        Returns: 'queued', 'started', 'finished', 'failed', or 'not_found'
        """
        job_id = f"deployment:{deployment_id}"
        
        # Check each registry for the job
        if self._queue.fetch_job(job_id):
            return 'queued'
        if job_id in self._queue.started_job_registry:
            return 'started'
        if job_id in self._queue.finished_job_registry:
            return 'finished'
        if job_id in self._queue.failed_job_registry:
            return 'failed'
        
        return 'not_found' 