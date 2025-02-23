from datetime import datetime, timezone
from app.db.models.deployment import Deployment, DeploymentStatus, DeploymentPriority
from app.db.models.cluster import Cluster, ClusterStatus
from app.db.models import User
from app.exceptions import ValidationError
from app.db import db

class DeploymentService:
    @staticmethod
    def create_deployment(user: User, cluster_id: int, name: str, ram: int, cpu: int, gpu: int = 0, priority: int = DeploymentPriority.MEDIUM.value) -> Deployment:
        """
        Create a new deployment on a cluster.
        Validates resource requirements against cluster capacity.
        Sets initial status as PENDING.
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

            # Validate resource availability
            if ram > cluster.ram:
                raise ValidationError("Requested RAM exceeds cluster capacity", "INSUFFICIENT_RAM")
            if cpu > cluster.cpu:
                raise ValidationError("Requested CPU exceeds cluster capacity", "INSUFFICIENT_CPU")
            if gpu > cluster.gpu:
                raise ValidationError("Requested GPU exceeds cluster capacity", "INSUFFICIENT_GPU")

            # Check if deployment name already exists in cluster
            existing_deployment = Deployment.query.filter_by(
                cluster_id=cluster_id,
                name=name,
                status=DeploymentStatus.PENDING.value
            ).first()

            if existing_deployment:
                raise ValidationError(
                    "A deployment with this name already exists in this cluster",
                    "DEPLOYMENT_EXISTS"
                )

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
            return deployment

        except Exception as e:
            db.session.rollback()
            if isinstance(e, ValidationError):
                raise
            raise ValidationError("Failed to create deployment", "DATABASE_ERROR") from e

    @staticmethod
    def list_deployments(user: User, cluster_id: int = None, include_deleted: bool = False) -> list[Deployment]:
        """
        List all deployments for a user's organization.
        Optionally filter by cluster and include deleted deployments.
        """
        # First get all clusters for the organization
        org_clusters = Cluster.query.filter_by(
            organisation_id=user.organisation_id
        ).with_entities(Cluster.id).all()
        
        cluster_ids = [c.id for c in org_clusters]

        if not cluster_ids:
            return []

        # Base query - filter by organization's clusters
        query = Deployment.query.filter(Deployment.cluster_id.in_(cluster_ids))

        # Filter by specific cluster if provided
        if cluster_id:
            if cluster_id not in cluster_ids:
                raise ValidationError("Cluster not found or access denied", "CLUSTER_NOT_FOUND")
            query = query.filter_by(cluster_id=cluster_id)

        # Filter by status
        if not include_deleted:
            query = query.filter(Deployment.status != DeploymentStatus.DELETED.value)

        return query.order_by(Deployment.priority.desc(), Deployment.created_at.desc()).all()

    @staticmethod
    def get_deployment(user: User, deployment_id: int) -> Deployment:
        """
        Get a specific deployment by ID.
        Ensures user has access to the deployment through organization.
        """
        # First get all clusters for the organization
        org_clusters = Cluster.query.filter_by(
            organisation_id=user.organisation_id
        ).with_entities(Cluster.id).all()
        
        cluster_ids = [c.id for c in org_clusters]

        if not cluster_ids:
            raise ValidationError("Deployment not found", "DEPLOYMENT_NOT_FOUND")

        # Get deployment and verify it belongs to one of user's clusters
        deployment = Deployment.query.filter_by(id=deployment_id).first()

        if not deployment or deployment.cluster_id not in cluster_ids:
            raise ValidationError("Deployment not found", "DEPLOYMENT_NOT_FOUND")

        return deployment 