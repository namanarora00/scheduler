from datetime import datetime, timezone
from app.db.models.deployment import Deployment, DeploymentStatus, DeploymentPriority
from app.db.models.cluster import Cluster, ClusterStatus
from app.db.models import User
from app.exceptions import ValidationError
from app.db import db
from app.services.queue_service import QueueService
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Optional

class DeploymentService:
    @staticmethod
    def create_deployment(user: User, cluster_id: int, name: str, ram: int, cpu: int, gpu: int = 0, priority: int = DeploymentPriority.MEDIUM.value) -> Deployment:
        """
        Create a new deployment on a cluster.
        Validates resource requirements against cluster capacity.
        Sets initial status as PENDING and adds to Redis queue.
        Priority must be between 1-5 (default: 3-MEDIUM)
        """
        try:
            # Validate resource values
            if ram <= 0 or cpu <= 0 or gpu < 0:
                raise ValidationError("Invalid resource values", "INVALID_RESOURCES")

            # Validate priority
            if not DeploymentPriority.is_valid(priority):
                raise ValidationError(
                    "Invalid priority. Must be between 1-5",
                    "INVALID_PRIORITY"
                )

            # Get and validate cluster
            cluster = Cluster.query.filter_by(
                id=cluster_id,
                organisation_id=user.organisation_id,
                status=ClusterStatus.ACTIVE.value
            ).first()

            if not cluster:
                raise ValidationError("Cluster not found or not active", "CLUSTER_NOT_FOUND")

            # Check for existing deployment with same name in this cluster
            existing_deployment = Deployment.query.filter_by(
                cluster_id=cluster_id,
                name=name
            ).filter(Deployment.status != DeploymentStatus.DELETED.value).first()

            if existing_deployment:
                print(f"Found existing deployment {existing_deployment.id} with name {name}")
                # Only re-queue if it's in PENDING state and not already in queue
                if existing_deployment.status == DeploymentStatus.PENDING.value:
                    
                    queue_service = QueueService.get_instance()
                    queue_status = queue_service.get_deployment_status(existing_deployment.id)
                    print(f"Existing deployment queue status: {queue_status}")

                    if queue_status in ('not_found', 'failed'):
                        queue_service.enqueue_deployment(existing_deployment.id, delay=10)


                return existing_deployment

            print(f"Creating new deployment with name {name}")
            deployment = Deployment(
                name=name,
                cluster_id=cluster_id,
                ram=ram,
                cpu=cpu,
                gpu=gpu,
                priority=priority,
                status=DeploymentStatus.PENDING.value,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            db.session.add(deployment)
            db.session.commit()
            print(f"Created new deployment with ID {deployment.id}")

            # Add deployment to Redis queue
            queue_service = QueueService.get_instance()
            queue_service.enqueue_deployment(deployment.id)
            print(f"Added deployment {deployment.id} to queue")

            return deployment

        except SQLAlchemyError as e:
            print(f"Error creating deployment: {e}")
            db.session.rollback()
            if isinstance(e, ValidationError):
                raise e
            raise ValidationError("Failed to create deployment", "DATABASE_ERROR") from e

    @staticmethod
    def list_deployments(user: User, cluster_id: int = None, include_deleted: bool = False) -> list[Deployment]:
        """
        List all deployments for a user's organization.
        Optionally filter by cluster and include deleted deployments.
        """
        org_clusters = Cluster.query.filter_by(
            organisation_id=user.organisation_id
        ).with_entities(Cluster.id).all()
        
        cluster_ids = [c.id for c in org_clusters]

        if not cluster_ids:
            return []

        query = Deployment.query.filter(Deployment.cluster_id.in_(cluster_ids))

        if cluster_id:
            if cluster_id not in cluster_ids:
                raise ValidationError("Cluster not found or access denied", "CLUSTER_NOT_FOUND")
            query = query.filter_by(cluster_id=cluster_id)

        if not include_deleted:
            query = query.filter(Deployment.status != DeploymentStatus.DELETED.value)

        deployments = query.order_by(Deployment.priority.desc(), Deployment.created_at.desc()).all()

        # Add queue status for pending deployments
        queue_service = QueueService.get_instance()
        for deployment in deployments:
            if deployment.status == DeploymentStatus.PENDING.value:
                deployment.queue_status = queue_service.get_deployment_status(deployment.id)

        return deployments

    @staticmethod
    def get_deployment(deployment_id: int) -> Optional[Deployment]:
        """Get deployment details"""
        try:
            deployment = Deployment.query.get(deployment_id)
            return deployment
        except SQLAlchemyError as e:
            raise ValidationError("Failed to get deployment", "DATABASE_ERROR") from e

    @staticmethod
    def update_deployment_status(deployment_id: int, status: str) -> Deployment:
        """Update the status of a deployment"""
        try:
            with db.session.begin_nested():
                deployment = Deployment.query.get(deployment_id)
                if not deployment:
                    raise ValidationError("Deployment not found", "DEPLOYMENT_NOT_FOUND")
                
                deployment.status = status
                deployment.updated_at = datetime.now(timezone.utc)
                db.session.commit()
                return deployment
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValidationError("Failed to update deployment status", "DATABASE_ERROR") from e

    @staticmethod
    def preempt_deployments_and_schedule_new(new_deployment_id: int, deployment_ids: List[int]) -> List[Deployment]:
        """Preempt multiple deployments by setting their status to pending and schedule a new deployment"""
        try:
            with db.session.begin_nested():
                deployments = []
                for dep_id in deployment_ids:
                    deployment = Deployment.query.get(dep_id)
                    if deployment:
                        deployment.status = DeploymentStatus.PENDING.value
                        deployment.updated_at = datetime.now(timezone.utc)
                        deployments.append(deployment)
            
                new_deployment = Deployment.query.get(new_deployment_id)

                if new_deployment:
                    new_deployment.status = DeploymentStatus.RUNNING.value
                    new_deployment.updated_at = datetime.now(timezone.utc)
                
                db.session.commit()
                
                # Re-queue preempted deployments
                queue_service = QueueService.get_instance()
                for deployment in deployments:
                    # preempted deployments are re-queued with a delay of 10 seconds
                    queue_service.enqueue_deployment(deployment.id, delay=10)
                    
                return deployments
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValidationError("Failed to preempt deployments", "DATABASE_ERROR") from e

    @staticmethod
    def get_cluster_deployments(cluster_id: int) -> Dict:
        """Get all deployments for a cluster with their current status"""
        try:
            cluster = Cluster.query.filter_by(
                id=cluster_id,
                status=ClusterStatus.ACTIVE.value
            ).first()
            
            if not cluster:
                raise ValidationError("Cluster not found or not active", "CLUSTER_NOT_FOUND")
            
            running_deployments = Deployment.query.filter_by(
                cluster_id=cluster_id,
                status=DeploymentStatus.RUNNING.value
            ).all()
            
            return {
                'cluster': {
                    'id': cluster.id,
                    'ram': cluster.ram,
                    'cpu': cluster.cpu,
                    'gpu': cluster.gpu,
                },
                'running_deployments': [{
                    'id': d.id,
                    'name': d.name,
                    'ram': d.ram,
                    'cpu': d.cpu,
                    'gpu': d.gpu,
                    'priority': d.priority,
                    'status': d.status,
                    'created_at': d.created_at.isoformat()
                } for d in running_deployments]
            }
        except SQLAlchemyError as e:
            raise ValidationError("Failed to get cluster deployments", "DATABASE_ERROR") from e 
    