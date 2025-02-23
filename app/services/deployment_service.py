from datetime import datetime, timezone
from app.db.models.deployment import Deployment, DeploymentStatus, DeploymentPriority
from app.db.models.cluster import Cluster, ClusterStatus
from app.db.models import User
from app.exceptions import ValidationError
from app.db import db
from app.services.queue_service import QueueService
from sqlalchemy.exc import SQLAlchemyError

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
                        print(f"Re-queueing deployment {existing_deployment.id}")
                        queue_service.enqueue_deployment(existing_deployment.id)
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
    def get_deployment(user: User, deployment_id: int) -> Deployment:
        """
        Get a specific deployment by ID.
        Ensures user has access to the deployment through organization.
        """
        org_clusters = Cluster.query.filter_by(
            organisation_id=user.organisation_id
        ).with_entities(Cluster.id).all()
        
        cluster_ids = [c.id for c in org_clusters]

        if not cluster_ids:
            raise ValidationError("Deployment not found", "DEPLOYMENT_NOT_FOUND")

        deployment = Deployment.query.filter_by(id=deployment_id).first()

        if not deployment or deployment.cluster_id not in cluster_ids:
            raise ValidationError("Deployment not found", "DEPLOYMENT_NOT_FOUND")

        # Add queue status for pending deployments
        if deployment.status == DeploymentStatus.PENDING.value:
            queue_service = QueueService.get_instance()
            deployment.queue_status = queue_service.get_deployment_status(deployment.id)

        return deployment 
    