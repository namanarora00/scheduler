from flask import Blueprint, request, jsonify
from app.services.cluster_service import ClusterService
from app.services.user_service import UserService
from app.exceptions import ServiceException, ValidationError
from app.middleware.auth import requires_auth, requires_role, Role

cluster_bp = Blueprint('cluster', __name__)

@cluster_bp.route('/', methods=['POST'])
@requires_auth
@requires_role(Role.ADMIN)
def create_cluster():
    """Create a new cluster"""
    try:
        data = request.get_json()
        name = data.get('name')
        ram = data.get('ram')
        cpu = data.get('cpu')
        gpu = data.get('gpu', 0)  # GPU is optional, defaults to 0

        if not all([name, ram, cpu]):
            raise ValidationError("Missing required fields", "MISSING_REQUIRED_FIELDS")

        try:
            ram = int(ram)
            cpu = int(cpu)
            gpu = int(gpu)
        except (TypeError, ValueError):
            raise ValidationError("Resource values must be integers", "INVALID_RESOURCE_TYPE")

        admin = UserService.get_user_by_id(request.user['user_id'])
        cluster = ClusterService.create_cluster(admin, name, ram, cpu, gpu)

        return jsonify({
            'message': 'Cluster created successfully',
            'cluster': {
                'id': cluster.id,
                'name': cluster.name,
                'ram': cluster.ram,
                'cpu': cluster.cpu,
                'gpu': cluster.gpu,
                'status': cluster.status,
                'created_at': cluster.created_at.isoformat()
            }
        }), 201

    except ServiceException as e:
        raise

@cluster_bp.route('/', methods=['GET'])
@requires_auth
def list_clusters():
    """List all clusters for the organization"""
    try:
        include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        user = UserService.get_user_by_id(request.user['user_id'])
        clusters = ClusterService.list_clusters(user, include_deleted)

        return jsonify({
            'clusters': [{
                'id': cluster.id,
                'name': cluster.name,
                'ram': cluster.ram,
                'cpu': cluster.cpu,
                'gpu': cluster.gpu,
                'status': cluster.status,
                'created_at': cluster.created_at.isoformat(),
                'updated_at': cluster.updated_at.isoformat()
            } for cluster in clusters]
        }), 200

    except ServiceException as e:
        raise

@cluster_bp.route('/<int:cluster_id>', methods=['DELETE'])
@requires_auth
@requires_role(Role.ADMIN)
def delete_cluster(cluster_id):
    """Soft delete a cluster"""
    try:
        admin = UserService.get_user_by_id(request.user['user_id'])
        cluster = ClusterService.delete_cluster(admin, cluster_id)

        return jsonify({
            'message': 'Cluster deleted successfully',
            'cluster': {
                'id': cluster.id,
                'name': cluster.name,
                'status': cluster.status,
                'updated_at': cluster.updated_at.isoformat()
            }
        }), 200

    except ServiceException as e:
        raise 