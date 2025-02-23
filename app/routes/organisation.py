from flask import Blueprint, request, jsonify
from app.services.org_service import OrgService
from app.middleware.auth import requires_auth
from app.exceptions import ServiceException, ValidationError

org_bp = Blueprint('organisation', __name__)


@org_bp.route('/<int:org_id>', methods=['GET'])
@requires_auth
def get_org(org_id):
    """Get organization details"""
    try:
        # Verify user belongs to the organization
        if request.user['organisation_id'] != org_id:
            raise ValidationError("Access denied", "ORG_ACCESS_DENIED")

        org = OrgService.get_organisation(org_id)
        return jsonify({
            'id': org.id,
            'name': org.name,
            'created_at': org.created_at.isoformat(),
            'updated_at': org.updated_at.isoformat()
        }), 200

    except ServiceException as e:
        raise
