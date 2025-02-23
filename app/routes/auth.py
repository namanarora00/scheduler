from flask import Blueprint, request, jsonify
from app.middleware.auth import requires_auth, AuthService
from app.services.user_service import UserService
from app.exceptions import ServiceException, ValidationError   

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        invite_code = data.get('invite_code')
        
        if not all([email, password, invite_code]):
            raise ValidationError("Missing required fields", "MISSING_REQUIRED_FIELDS")
            
        user = UserService.create_user(email, password, invite_code)
        token = AuthService.create_access_token(user)
        
        return jsonify({
            'message': 'User created successfully',
            'token': token
        }), 201
        
    except ServiceException as e:
        raise

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not all([email, password]):
            raise ValidationError("Missing required fields", "MISSING_REQUIRED_FIELDS")
            
        user = AuthService.authenticate_user(email, password)
        token = AuthService.create_access_token(user)
        
        return jsonify({
            'message': 'Login successful',
            'token': token
        }), 200
        
    except ServiceException as e:
        raise

@auth_bp.route('/me', methods=['GET'])
@requires_auth
def get_current_user():
    try:
        user = UserService.get_user_by_id(request.user['user_id'])
        return jsonify({
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'organisation_id': user.organisation_id
        }), 200
    except ServiceException as e:
        raise
