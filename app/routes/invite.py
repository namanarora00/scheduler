from flask import Blueprint, request, jsonify
from app.services.invite_service import InviteService
from app.services.user_service import UserService
from app.exceptions import ServiceException, ValidationError
from app.middleware.auth import Role, requires_auth, requires_role


invite_bp = Blueprint('invite', __name__)

@invite_bp.route('/', methods=['POST'])
@requires_auth
@requires_role(Role.ADMIN)
def create_invite():
    """Create a new invite code"""
    try:
        data = request.get_json()
        email = data.get('email')
        role = data.get('role')

        if not all([email, role]):
            raise ValidationError("Missing required fields", "MISSING_REQUIRED_FIELDS")

        admin = UserService.get_user_by_id(request.user['user_id'])
        invite = InviteService.create_invite(admin, email, role)

        return jsonify({
            'message': 'Invite code created successfully',
            'invite': {
                'code': invite.code,
                'email': invite.user_email,
                'role': invite.role,
                'valid_until': invite.valid_until.isoformat()
            }
        }), 201

    except ServiceException as e:
        raise

@invite_bp.route('/', methods=['GET'])
@requires_auth
@requires_role(Role.ADMIN)
def list_invites():
    """List all invite codes"""
    try:
        include_used = request.args.get('include_used', '').lower() == 'true'
        admin = UserService.get_user_by_id(request.user['user_id'])
        invites = InviteService.list_invites(admin, include_used)

        return jsonify({
            'invites': [{
                'id': invite.id,
                'code': invite.code,
                'email': invite.user_email,
                'role': invite.role,
                'is_used': invite.is_used,
                'valid_until': invite.valid_until.isoformat(),
                'created_at': invite.created_at.isoformat()
            } for invite in invites]
        }), 200

    except ServiceException as e:
        raise

