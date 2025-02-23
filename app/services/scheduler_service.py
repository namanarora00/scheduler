from typing import List, Dict, Optional, Tuple, Protocol
from datetime import datetime, timezone
from app.db.models.deployment import Deployment, DeploymentStatus, DeploymentPriority
from app.db.models.cluster import Cluster, ClusterStatus
from app.db import db
from app.utils.redis_lock import RedisLock
from app.services.queue_service import QueueService
from redis import Redis
from sqlalchemy.exc import SQLAlchemyError
from dataclasses import dataclass

@dataclass
class ResourceSpec:
    ram: int
    cpu: int
    gpu: int

@dataclass
class ClusterInfo:
    id: int
    resources: ResourceSpec
    running_deployments: List['DeploymentInfo']

@dataclass
class DeploymentInfo:
    id: int
    name: str
    cluster_id: int
    resources: ResourceSpec
    priority: int
    status: str
    created_at: datetime

class ResourceManager:
    @staticmethod
    def calculate_used_resources(deployments: List[DeploymentInfo]) -> ResourceSpec:
        """Calculate total resources used by deployments"""
        return ResourceSpec(
            ram=sum(d.resources.ram for d in deployments),
            cpu=sum(d.resources.cpu for d in deployments),
            gpu=sum(d.resources.gpu for d in deployments)
        )

    @staticmethod
    def can_fit_deployment(deployment: DeploymentInfo, available: ResourceSpec) -> bool:
        """Check if deployment can fit in available resources"""
        return (deployment.resources.ram <= available.ram and
                deployment.resources.cpu <= available.cpu and
                deployment.resources.gpu <= available.gpu)

    @staticmethod
    def calculate_resource_utilization(resources: ResourceSpec) -> float:
        """Calculate resource utilization score"""
        return resources.ram + resources.cpu + resources.gpu

    @staticmethod
    def calculate_resource_efficiency(actual: ResourceSpec, required: ResourceSpec) -> float:
        """Calculate how efficiently resources match what's needed (lower is better)"""
        ram_waste = max(0, actual.ram - required.ram)
        cpu_waste = max(0, actual.cpu - required.cpu)
        gpu_waste = max(0, actual.gpu - required.gpu)
        return ram_waste + cpu_waste + gpu_waste

class SchedulerCore:
    def __init__(self):
        self.resource_manager = ResourceManager()

    def find_preemptible_deployments(
        self,
        running_deployments: List[DeploymentInfo],
        required_deployment: DeploymentInfo
    ) -> List[DeploymentInfo]:
        """
        Find deployments that can be preempted using a greedy approach.
        Pure function with no side effects.
        """
        # Filter deployments with lower priority
        candidates = [
            d for d in running_deployments
            if d.priority < required_deployment.priority
        ]

        if not candidates:
            return []

        # Sort by utilisation and priority, to make sure we have the max number of deployments running.
        
        sorted_candidates = sorted(
            candidates,
            key=lambda d: (
                -self.resource_manager.calculate_resource_utilization(d.resources), # Higher utilization
                d.priority 
            )
        )

        to_preempt = []
        acquired = ResourceSpec(ram=0, cpu=0, gpu=0)

        
        # Actually selecting the deployments.
        for deployment in sorted_candidates:
            if (acquired.ram >= required_deployment.resources.ram and
                acquired.cpu >= required_deployment.resources.cpu and
                acquired.gpu >= required_deployment.resources.gpu):
                break

            to_preempt.append(deployment)
            acquired.ram += deployment.resources.ram
            acquired.cpu += deployment.resources.cpu
            acquired.gpu += deployment.resources.gpu

        # Verify we got enough resources
        if (acquired.ram < required_deployment.resources.ram or
            acquired.cpu < required_deployment.resources.cpu or
            acquired.gpu < required_deployment.resources.gpu):
            return []

        return to_preempt

    def can_schedule_deployment(
        self,
        deployment: DeploymentInfo,
        cluster: ClusterInfo
    ) -> Tuple[bool, List[DeploymentInfo]]:
        """
        Check if a deployment can be scheduled, either directly or through preemption.
        """
        # Calculate available resources
        used = self.resource_manager.calculate_used_resources(cluster.running_deployments)
        available = ResourceSpec(
            ram=cluster.resources.ram - used.ram,
            cpu=cluster.resources.cpu - used.cpu,
            gpu=cluster.resources.gpu - used.gpu
        )

        # Add directly. 
        if self.resource_manager.can_fit_deployment(deployment, available):
            return True, []

        # Try removing some of the older deps
        # if we cannot fit even with preemption, this returns 0 deps
        to_preempt = self.find_preemptible_deployments(
            cluster.running_deployments,
            deployment
        )

        return len(to_preempt) > 0, to_preempt

class SchedulerService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.queue_service = QueueService.get_instance()
        self.scheduler_core = SchedulerCore()

    def _get_cluster_info(self, cluster: Cluster) -> ClusterInfo:
        """Convert DB cluster to ClusterInfo"""
        running_deployments = Deployment.query.filter_by(
            cluster_id=cluster.id,
            status=DeploymentStatus.RUNNING.value
        ).all()

        return ClusterInfo(
            id=cluster.id,
            resources=ResourceSpec(ram=cluster.ram, cpu=cluster.cpu, gpu=cluster.gpu),
            running_deployments=[
                DeploymentInfo(
                    id=d.id,
                    name=d.name,
                    cluster_id=d.cluster_id,
                    resources=ResourceSpec(ram=d.ram, cpu=d.cpu, gpu=d.gpu),
                    priority=d.priority,
                    status=d.status,
                    created_at=d.created_at
                ) for d in running_deployments
            ]
        )

    def _get_deployment_info(self, deployment: Deployment) -> DeploymentInfo:
        """Convert DB deployment to DeploymentInfo"""
        return DeploymentInfo(
            id=deployment.id,
            name=deployment.name,
            cluster_id=deployment.cluster_id,
            resources=ResourceSpec(ram=deployment.ram, cpu=deployment.cpu, gpu=deployment.gpu),
            priority=deployment.priority,
            status=deployment.status,
            created_at=deployment.created_at
        )

    def _preempt_deployments(self, deployments: List[DeploymentInfo]) -> None:
        """Handle database operations for preemption"""
        try:
            db.session.begin()
            for dep_info in deployments:
                deployment = Deployment.query.get(dep_info.id)
                if deployment:
                    deployment.status = DeploymentStatus.PENDING.value
                    deployment.updated_at = datetime.now(timezone.utc)
                    self.queue_service.enqueue_deployment(deployment.id)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise

    def try_schedule_deployment(self, deployment: Deployment) -> bool:
        """Database-aware wrapper around core scheduling logic"""
        if deployment.status == DeploymentStatus.RUNNING.value:
            return True

        cluster = Cluster.query.filter_by(
            id=deployment.cluster_id,
            status=ClusterStatus.ACTIVE.value
        ).first()

        if not cluster:
            return False

        # Try to acquire lock for this cluster
        with RedisLock(self.redis, f"cluster:{cluster.id}", expire_seconds=30) as lock:
            try:
                # Convert DB objects to info objects
                cluster_info = self._get_cluster_info(cluster)
                deployment_info = self._get_deployment_info(deployment)

                # Use core scheduler to make decision
                can_schedule, to_preempt = self.scheduler_core.can_schedule_deployment(
                    deployment_info, cluster_info
                )

                if not can_schedule:
                    return False

                db.session.begin()
                if to_preempt:
                    self._preempt_deployments(to_preempt)

                deployment.status = DeploymentStatus.RUNNING.value
                deployment.updated_at = datetime.now(timezone.utc)
                db.session.commit()
                return True

            except SQLAlchemyError:
                db.session.rollback()
                raise 