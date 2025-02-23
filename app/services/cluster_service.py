from datetime import datetime, timezone
from app.db.models.cluster import Cluster, ClusterStatus
from app.db.models import User
from app.exceptions import ValidationError
from app.db import db

class ClusterService:
    @staticmethod
    def create_cluster(admin_user: User, name: str, ram: int, cpu: int, gpu: int) -> Cluster:
        """
        Create a new cluster for an organization.
        Only admins can create clusters.
        """
        try:
            # Validate resource values
            if ram <= 0 or cpu <= 0 or gpu < 0:
                raise ValidationError("Invalid resource values", "INVALID_RESOURCES")

            # Check if cluster name already exists in org
            existing_cluster = Cluster.query.filter_by(
                organisation_id=admin_user.organisation_id,
                name=name,
                status=ClusterStatus.ACTIVE.value
            ).first()

            if existing_cluster:
                raise ValidationError(
                    "A cluster with this name already exists in your organization",
                    "CLUSTER_EXISTS"
                )

            cluster = Cluster(
                organisation_id=admin_user.organisation_id,
                name=name,
                ram=ram,
                cpu=cpu,
                gpu=gpu,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            db.session.add(cluster)
            db.session.commit()
            return cluster

        except Exception as e:
            db.session.rollback()
            if isinstance(e, ValidationError):
                raise
            raise ValidationError("Failed to create cluster", "DATABASE_ERROR") from e

    @staticmethod
    def list_clusters(user: User, include_deleted: bool = False) -> list[Cluster]:
        """
        List all clusters for an organization.
        Optionally include deleted clusters.
        """
        query = Cluster.query.filter_by(organisation_id=user.organisation_id)
        
        if not include_deleted:
            query = query.filter_by(status=ClusterStatus.ACTIVE.value)
            
        return query.order_by(Cluster.created_at.desc()).all()

    @staticmethod
    def delete_cluster(admin_user: User, cluster_id: int) -> Cluster:
        """
        Soft delete a cluster.
        Only admins can delete clusters.
        """
        try:
            cluster = Cluster.query.filter_by(
                id=cluster_id,
                organisation_id=admin_user.organisation_id
            ).first()

            if not cluster:
                raise ValidationError("Cluster not found", "CLUSTER_NOT_FOUND")

            if cluster.status == ClusterStatus.DELETED.value:
                raise ValidationError("Cluster is already deleted", "CLUSTER_ALREADY_DELETED")

            cluster.status = ClusterStatus.DELETED.value
            cluster.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            return cluster

        except Exception as e:
            db.session.rollback()
            if isinstance(e, ValidationError):
                raise
            raise ValidationError("Failed to delete cluster", "DATABASE_ERROR") from e 