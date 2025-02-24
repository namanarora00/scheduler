import os
import sys
import requests
import json
from redis import Redis
from rq import Worker, Queue, Connection
from datetime import datetime, timezone
from flask import Flask
from app.db import db, init_db
from app.db.models.deployment import Deployment, DeploymentStatus
from app.services.scheduler_service import SchedulerService
from app.services.queue_service import QueueService
from sqlalchemy.exc import SQLAlchemyError

# Initialize Flask app for database context
app = Flask(__name__)
init_db(app)

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:6000')
API_TOKEN = os.getenv('API_TOKEN', 'your_api_token_here')  # This should be set in environment

def get_headers():
    """Get headers for API requests"""
    return {
        'Authorization': f'Bearer {API_TOKEN}',
        'Content-Type': 'application/json'
    }

def process_deployment(deployment_id: int):
    """
    Process a deployment request.
    This function will be called by the RQ worker.
    :param deployment_id: ID of the deployment to process
    """
    print(f"\nProcessing deployment {deployment_id}")
    with app.app_context():
        try:

            # Create Redis connection for scheduler
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_client = Redis(host=redis_host, port=redis_port)
            
            # Try to schedule the deployment
            scheduler = SchedulerService(redis_client)
            print(f"Attempting to schedule deployment {deployment_id}")
            
            try:
                scheduled = scheduler.try_schedule_deployment(deployment_id)

                if not scheduled:
                    print(f"Could not schedule deployment {deployment_id}")
                    print(f"Re-enqueueing deployment {deployment_id} for later attempt with a delay.")

                    queue_service = QueueService.get_instance()
                    queue_service.enqueue_deployment(deployment_id, delay=10)
                    
                    return

                print(f"Successfully scheduled deployment {deployment_id}")

            except SQLAlchemyError as e:
                print(f"Database error processing deployment {deployment_id}: {str(e)}", file=sys.stderr)
                raise

        except Exception as e:
            print(f"Error processing deployment {deployment_id}: {str(e)}", file=sys.stderr)
            raise

if __name__ == '__main__':
    # Get Redis connection settings from environment
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    
    print(f"\nStarting worker with Redis at {redis_host}:{redis_port}")
    # Connect to Redis
    redis_conn = Redis(host=redis_host, port=redis_port)
    
    # Start the worker
    with Connection(redis_conn):
        worker = Worker(['deployments'])
        print("Worker ready to process deployments")
        worker.work() 