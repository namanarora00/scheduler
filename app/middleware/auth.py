from enum import Enum
from functools import wraps
from flask import request
from app.exceptions import AuthenticationError, AuthorizationError, ServiceException

import jwt
import os

from datetime import datetime, timedelta
from app.db.models import User
from werkzeug.security import check_password_hash

from dotenv import load_dotenv


load_dotenv()

JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)


class Role(Enum):
    ADMIN = "admin"
    DEV = "dev"
    VIEWER = "viewer"

ROLE_PRIORITY = {
    'admin': 3,
    'dev': 2,
    'viewer': 1
}


class AuthService:
    @staticmethod
    def verify_password(user: User, password: str) -> bool:
        return check_password_hash(user.password_hash, password)
        
    @staticmethod
    def authenticate_user(email: str, password: str) -> User:
        try:
            user = User.query.filter_by(email=email).first()
            if not AuthService.verify_password(user, password):
                raise AuthenticationError("Invalid email or password", "INVALID_CREDENTIALS")
            return user
        except Exception as e:
            raise AuthenticationError("Invalid email or password", "INVALID_CREDENTIALS")
        
    @staticmethod
    def create_access_token(user: User) -> str:
        payload = {
            'user_id': user.id,
            'email': user.email,
            'role': user.role,
            'organisation_id': user.organisation_id,
            'exp': datetime.utcnow() + JWT_ACCESS_TOKEN_EXPIRES
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
    @staticmethod
    def verify_token(token: str) -> dict:
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired", "TOKEN_EXPIRED")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token", "INVALID_TOKEN")
            
    @staticmethod
    def check_role_access(user_role: str, required_role: str) -> bool:
        """
        Check if the user's role has sufficient priority to access a resource
        that requires the specified role.
        """
        user_priority = ROLE_PRIORITY.get(user_role, 0)
        required_priority = ROLE_PRIORITY.get(required_role, 0)
        
        return user_priority >= required_priority 

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                raise AuthenticationError("Invalid token format", "INVALID_TOKEN_FORMAT")
                
        if not token:
            raise AuthenticationError("Token is missing", "TOKEN_MISSING")
            
        try:
            payload = AuthService.verify_token(token)
            request.user = payload
            return f(*args, **kwargs)
        except ServiceException as e:
            raise AuthenticationError(str(e))
            
    return decorated


# exports, 
# decorator utils for routes.

def requires_role(required_role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(request, 'user'): # this is only used after the requires auth decorator.
                raise AuthenticationError("Authentication required", "AUTH_REQUIRED")
                
            user_role = request.user.get('role')
            if not user_role:
                raise AuthorizationError("User has no role assigned", "NO_ROLE_ASSIGNED")
                
            if not AuthService.check_role_access(user_role, required_role):
                raise AuthorizationError(
                    f"Access denied. Required role: {required_role}",
                    "INSUFFICIENT_ROLE"
                )
                
            return f(*args, **kwargs)
        return decorated
    return decorator