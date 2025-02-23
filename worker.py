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
    print(f"\nProcessing deployment {deployment_id}")
    with app.app_context():
        try:
            # Get deployment
            deployment = Deployment.query.get(deployment_id)
            if not deployment:
                print(f"Error: Deployment {deployment_id} not found in database")
                raise Exception(f"Deployment {deployment_id} not found")

            print(f"Found deployment: {deployment.name} (Status: {deployment.status})")
            print(f"Resources requested - RAM: {deployment.ram}GB, CPU: {deployment.cpu}, GPU: {deployment.gpu}")
            print(f"Priority: {deployment.priority}")

            # Create Redis connection for scheduler
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_client = Redis(host=redis_host, port=redis_port)
            
            # Try to schedule the deployment
            scheduler = SchedulerService(redis_client)
            print(f"Attempting to schedule deployment {deployment_id}")
            
    
            try: 
                db.session.begin()
            except: 
                # if there is a txn thats already running we don't care. 
                pass

            try:
                scheduled = scheduler.try_schedule_deployment(deployment)
                
                if not scheduled:
                    print(f"Could not schedule deployment {deployment_id}")
                    print("Checking cluster resources...")
                    

                    print(f"Re-enqueueing deployment {deployment_id} for later attempt with a delay.")
                    import time
                    time.sleep(10)

                    queue_service = QueueService.get_instance()
                    queue_service.enqueue_deployment(deployment_id)

                    db.session.rollback()


                    return

                print(f"Successfully scheduled deployment {deployment_id}")
                db.session.commit()

            except SQLAlchemyError as e:
                print(f"Database error processing deployment {deployment_id}: {str(e)}", file=sys.stderr)
                db.session.rollback()
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