import os
import sys
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

def process_deployment(deployment_id: int):
    """
    Process a deployment request.
    This function will be called by the RQ worker.
    :param deployment_id: ID of the deployment to process
    """
    with app.app_context():
        try:
            # Get deployment
            deployment = Deployment.query.get(deployment_id)
            if not deployment:
                raise Exception(f"Deployment {deployment_id} not found")

            # Create Redis connection for scheduler
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_client = Redis(host=redis_host, port=redis_port)
            
            # Try to schedule the deployment
            scheduler = SchedulerService(redis_client)
            scheduled = scheduler.try_schedule_deployment(deployment)
            
            if not scheduled:
                print(f"Could not schedule deployment {deployment_id}, re-enqueueing...", file=sys.stderr)

                queue_service = QueueService.get_instance()
                
                queue_service.enqueue_deployment(deployment_id)
                return

        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Database error processing deployment {deployment_id}: {str(e)}", file=sys.stderr)
            raise

        except Exception as e:
            # Log the error and optionally update deployment status
            print(f"Error processing deployment {deployment_id}: {str(e)}", file=sys.stderr)
            raise

if __name__ == '__main__':
    # Get Redis connection settings from environment
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    
    # Connect to Redis
    redis_conn = Redis(host=redis_host, port=redis_port)
    
    # Start the worker
    with Connection(redis_conn):
        worker = Worker(['deployments'])
        worker.work() 