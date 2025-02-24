from flask import Blueprint, request, jsonify
from app.services.deployment_service import DeploymentService
from app.services.user_service import UserService
from app.exceptions import ServiceException, ValidationError
from app.middleware.auth import requires_auth
from app.db.models.deployment import DeploymentPriority

deployment_bp = Blueprint('deployment', __name__)

@deployment_bp.route('/', methods=['POST'])
@requires_auth
def create_deployment():
    """Create a new deployment"""
    try:
        data = request.get_json()
        name = data.get('name')
        cluster_id = data.get('cluster_id')
        ram = data.get('ram')
        cpu = data.get('cpu')
        gpu = data.get('gpu', 0)  # GPU is optional, defaults to 0
        priority = data.get('priority', DeploymentPriority.MEDIUM.value)  # Priority is optional, defaults to MEDIUM

        if not all([name, cluster_id, ram, cpu]):
            raise ValidationError("Missing required fields", "MISSING_REQUIRED_FIELDS")

        try:
            cluster_id = int(cluster_id)
            ram = int(ram)
            cpu = int(cpu)
            gpu = int(gpu)
            priority = int(priority)
        except (TypeError, ValueError):
            raise ValidationError("Invalid field types", "INVALID_FIELD_TYPE")

        user = UserService.get_user_by_id(request.user['user_id'])
        deployment = DeploymentService.create_deployment(
            user, cluster_id, name, ram, cpu, gpu, priority
        )

        return jsonify({
            'message': 'Deployment created successfully',
            'deployment': {
                'id': deployment.id,
                'name': deployment.name,
                'cluster_id': deployment.cluster_id,
                'ram': deployment.ram,
                'cpu': deployment.cpu,
                'gpu': deployment.gpu,
                'priority': deployment.priority,
                'status': deployment.status,
                'created_at': deployment.created_at.isoformat()
            }
        }), 201

    except ServiceException as e:
        raise

@deployment_bp.route('/', methods=['GET'])
@requires_auth
def list_deployments():
    """List all deployments"""
    try:
        cluster_id = request.args.get('cluster_id')
        include_deleted = request.args.get('include_deleted', '').lower() == 'true'

        if cluster_id:
            try:
                cluster_id = int(cluster_id)
            except ValueError:
                raise ValidationError("Invalid cluster ID", "INVALID_CLUSTER_ID")

        user = UserService.get_user_by_id(request.user['user_id'])
        deployments = DeploymentService.list_deployments(user, cluster_id, include_deleted)

        return jsonify({
            'deployments': [{
                'id': d.id,
                'name': d.name,
                'cluster_id': d.cluster_id,
                'ram': d.ram,
                'cpu': d.cpu,
                'gpu': d.gpu,
                'priority': d.priority,
                'status': d.status,
                'created_at': d.created_at.isoformat(),
                'updated_at': d.updated_at.isoformat()
            } for d in deployments]
        }), 200

    except ServiceException as e:
        raise

@deployment_bp.route('/<int:deployment_id>', methods=['GET'])
@requires_auth
def get_deployment(deployment_id):
    """Get a specific deployment"""
    try:
        user = UserService.get_user_by_id(request.user['user_id'])
        deployment = DeploymentService.get_deployment(deployment_id)

        if not deployment:
            return jsonify({'error': 'Deployment not found'}), 404
        
        return jsonify({
            'deployment': {
                'id': deployment.id,
                'name': deployment.name,
                'cluster_id': deployment.cluster_id,
                'ram': deployment.ram,
                'cpu': deployment.cpu,
                'gpu': deployment.gpu,
                'priority': deployment.priority,
                'status': deployment.status,
                'created_at': deployment.created_at.isoformat(),
                'updated_at': deployment.updated_at.isoformat()
            }
        }), 200

    except ServiceException as e:
        raise 