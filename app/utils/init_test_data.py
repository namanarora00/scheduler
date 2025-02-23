from datetime import datetime, timezone
from app.db import db
from app.db.models import Organisation, User, Cluster, Deployment, InviteCode
from app.db.models.deployment import DeploymentStatus, DeploymentPriority
from app.db.models.cluster import ClusterStatus

def init_test_data():
    """Initialize test data in the database"""
    try:
        print("\nChecking for existing test data...")
        # Check if test data already exists
        if User.query.filter_by(email="admin@test.com").first():
            print("Test data already exists")
            return

        print("Creating new test data...")
        # Create test organization
        org = Organisation(
            name="Test Organization",
            description="A test organization for development purposes",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.session.add(org)
        db.session.flush()
        print(f"Created organization with ID: {org.id}")

        # Create invite codes
        admin_invite = InviteCode(
            code="ADMIN_SETUP",
            user_email="admin@test.com",
            role="admin",
            organisation_id=org.id,
            created_at=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc),
            is_used=False
        )
        db.session.add(admin_invite)
        db.session.flush()
        print(f"Created admin invite code with ID: {admin_invite.id}")

        dev_invite = InviteCode(
            code="DEV_SETUP",
            user_email="dev@test.com",
            role="dev",
            organisation_id=org.id,
            created_at=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc),
            is_used=False
        )
        db.session.add(dev_invite)
        db.session.flush()
        print(f"Created dev invite code with ID: {dev_invite.id}")

        # Create admin user
        admin = User(
            email="admin@test.com",
            organisation_id=org.id,
            invite_code_id=admin_invite.id,
            role="admin",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        admin.set_password("admin123")
        db.session.add(admin)
        admin_invite.is_used = True
        db.session.flush()
        print(f"Created admin user with ID: {admin.id}")

        # Create developer user
        dev = User(
            email="dev@test.com",
            organisation_id=org.id,
            invite_code_id=dev_invite.id,
            role="dev",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        dev.set_password("dev123")
        db.session.add(dev)
        dev_invite.is_used = True
        db.session.flush()
        print(f"Created developer user with ID: {dev.id}")

        # Create test clusters
        cluster1 = Cluster(
            name="test-cluster-1",
            organisation_id=org.id,
            ram=16,
            cpu=8,
            gpu=2,
            status=ClusterStatus.ACTIVE.value,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.session.add(cluster1)
        db.session.flush()
        print(f"Created cluster 1 with ID: {cluster1.id}")

        cluster2 = Cluster(
            name="test-cluster-2",
            organisation_id=org.id,
            ram=32,
            cpu=16,
            gpu=4,
            status=ClusterStatus.ACTIVE.value,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.session.add(cluster2)
        db.session.flush()
        print(f"Created cluster 2 with ID: {cluster2.id}")

        # Create some test deployments
        deployments = [
            Deployment(
                name="test-deployment-1",
                cluster_id=cluster1.id,
                ram=4,
                cpu=2,
                gpu=1,
                priority=DeploymentPriority.HIGH.value,
                status=DeploymentStatus.RUNNING.value,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            
        ]

        for i, deployment in enumerate(deployments, 1):
            db.session.add(deployment)
            db.session.flush()
            print(f"Created deployment {i} with ID: {deployment.id}")

        db.session.commit()
        print("\nTest data initialization completed successfully!")
        print("\nTest Credentials:")
        print("Admin User - Email: admin@test.com, Password: admin123")
        print("Dev User - Email: dev@test.com, Password: dev123")

        # Verify the data was saved
        admin_check = User.query.filter_by(email="admin@test.com").first()
        if admin_check:
            print(f"\nVerification: Admin user found in database with ID: {admin_check.id}")
        else:
            print("\nWarning: Admin user not found in database after creation!")

    except Exception as e:
        db.session.rollback()
        print(f"Error initializing test data: {str(e)}")
        raise 