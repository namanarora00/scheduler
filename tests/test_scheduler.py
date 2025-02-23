from datetime import datetime, timezone
from app.services.scheduler_service import (
    SchedulerCore,
    ResourceManager,
    ResourceSpec,
    DeploymentInfo,
    ClusterInfo
)

def create_deployment_info(
    id: int,
    ram: int,
    cpu: int,
    gpu: int,
    priority: int,
    name: str = "test-deployment"
) -> DeploymentInfo:
    """Helper to create test deployment info"""
    return DeploymentInfo(
        id=id,
        name=name,
        cluster_id=1,
        resources=ResourceSpec(ram=ram, cpu=cpu, gpu=gpu),
        priority=priority,
        status="running",
        created_at=datetime.now(timezone.utc)
    )

def create_cluster_info(
    ram: int,
    cpu: int,
    gpu: int,
    running_deployments: list[DeploymentInfo]
) -> ClusterInfo:
    """Helper to create test cluster info"""
    return ClusterInfo(
        id=1,
        resources=ResourceSpec(ram=ram, cpu=cpu, gpu=gpu),
        running_deployments=running_deployments
    )

def test_resource_manager_calculations():
    """Test resource calculation methods"""
    rm = ResourceManager()
    
    # Test used resources calculation
    deployments = [
        create_deployment_info(1, ram=2, cpu=1, gpu=0, priority=1),
        create_deployment_info(2, ram=3, cpu=2, gpu=1, priority=2)
    ]
    used = rm.calculate_used_resources(deployments)
    assert used.ram == 5
    assert used.cpu == 3
    assert used.gpu == 1

    # Test can_fit_deployment
    deployment = create_deployment_info(3, ram=4, cpu=2, gpu=0, priority=3)
    available = ResourceSpec(ram=6, cpu=3, gpu=1)
    assert rm.can_fit_deployment(deployment, available) == True

    available = ResourceSpec(ram=3, cpu=1, gpu=0)
    assert rm.can_fit_deployment(deployment, available) == False

def test_scheduler_direct_fit():
    """Test scheduling when deployment fits directly"""
    scheduler = SchedulerCore()
    
    # Create a cluster with plenty of resources
    cluster = create_cluster_info(
        ram=10,
        cpu=5,
        gpu=2,
        running_deployments=[
            create_deployment_info(1, ram=2, cpu=1, gpu=0, priority=1)
        ]
    )
    
    # Try to schedule a deployment that fits
    deployment = create_deployment_info(2, ram=4, cpu=2, gpu=1, priority=3)
    can_schedule, to_preempt = scheduler.can_schedule_deployment(deployment, cluster)
    
    assert can_schedule == True
    assert len(to_preempt) == 0

def test_scheduler_needs_preemption():
    """Test scheduling when preemption is needed"""
    scheduler = SchedulerCore()
    
    # Create a cluster with resources mostly used by lower priority deployments
    cluster = create_cluster_info(
        ram=10,
        cpu=5,
        gpu=2,
        running_deployments=[
            create_deployment_info(1, ram=6, cpu=3, gpu=1, priority=1),
            create_deployment_info(2, ram=2, cpu=1, gpu=0, priority=2)
        ]
    )
    
    # Try to schedule a high-priority deployment that needs preemption
    deployment = create_deployment_info(3, ram=7, cpu=4, gpu=1, priority=5)
    can_schedule, to_preempt = scheduler.can_schedule_deployment(deployment, cluster)
    
    assert can_schedule == True
    assert len(to_preempt) == 1
    assert to_preempt[0].id == 1  # Should preempt the larger, lower-priority deployment

def test_scheduler_cannot_fit():
    """Test scheduling when deployment cannot fit even with preemption"""
    scheduler = SchedulerCore()
    
    # Create a cluster with insufficient total resources
    cluster = create_cluster_info(
        ram=8,
        cpu=4,
        gpu=1,
        running_deployments=[
            create_deployment_info(1, ram=4, cpu=2, gpu=0, priority=1)
        ]
    )
    
    # Try to schedule a deployment that's too large
    deployment = create_deployment_info(2, ram=10, cpu=5, gpu=2, priority=5)
    can_schedule, to_preempt = scheduler.can_schedule_deployment(deployment, cluster)
    
    assert can_schedule == False
    assert len(to_preempt) == 0

def test_scheduler_preemption_optimization():
    """Test that scheduler optimizes preemption choices"""
    scheduler = SchedulerCore()
    
    # Create a cluster with several running deployments
    cluster = create_cluster_info(
        ram=20,
        cpu=10,
        gpu=4,
        running_deployments=[
            create_deployment_info(1, ram=4, cpu=2, gpu=0, priority=1),  # Small
            create_deployment_info(2, ram=8, cpu=4, gpu=1, priority=1),  # Large
            create_deployment_info(3, ram=4, cpu=2, gpu=1, priority=2),  # Medium
        ]
    )
    
    # Try to schedule a deployment that could fit by preempting either
    # one large or two small deployments
    deployment = create_deployment_info(4, ram=7, cpu=3, gpu=1, priority=3)
    can_schedule, to_preempt = scheduler.can_schedule_deployment(deployment, cluster)
    
    assert can_schedule == True
    assert len(to_preempt) == 1  # Should choose one larger deployment
    assert to_preempt[0].id == 2  # Should be the large, low-priority deployment

def test_scheduler_priority_respect():
    """Test that scheduler respects priority ordering"""
    scheduler = SchedulerCore()
    
    # Create a cluster with mixed priority deployments
    cluster = create_cluster_info(
        ram=20,
        cpu=10,
        gpu=4,
        running_deployments=[
            create_deployment_info(1, ram=4, cpu=2, gpu=0, priority=1),
            create_deployment_info(2, ram=4, cpu=2, gpu=0, priority=4),
            create_deployment_info(3, ram=4, cpu=2, gpu=0, priority=2)
        ]
    )
    
    # Try to schedule a deployment that needs preemption
    deployment = create_deployment_info(4, ram=8, cpu=4, gpu=0, priority=3)
    can_schedule, to_preempt = scheduler.can_schedule_deployment(deployment, cluster)
    
    assert can_schedule == True
    assert len(to_preempt) == 2
    # Should only preempt lower priority deployments
    assert all(d.priority < deployment.priority for d in to_preempt)
    # Should not preempt the priority 4 deployment
    assert all(d.priority != 4 for d in to_preempt) 