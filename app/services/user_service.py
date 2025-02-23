from datetime import datetime, timezone 
from app.db.models import User, InviteCode
from app.exceptions import ValidationError
from app.db import db
from app.utils.validators import validate_email, validate_password

class UserService:
    @staticmethod
    def create_user(email: str, password: str, invite_code: str) -> User:
        """
        Create a new user with the given email, password and invite code.
        Validates email uniqueness and invite code validity.
        Uses database transaction to ensure data consistency.
        """

        # validate email and password
        if not validate_email(email):
            raise ValidationError("Invalid email", "INVALID_EMAIL")
        if not validate_password(password):
            raise ValidationError("Invalid password. Must be at least 8 characters long.", "INVALID_PASSWORD")

        try:
            with db.session.begin_nested():
                if User.query.filter_by(email=email).first():
                    raise ValidationError("User with this email already exists", "USER_EXISTS")

                # row lock
                invite = InviteCode.query.with_for_update().filter_by(code=invite_code).first()

                if not invite:
                    raise ValidationError("Invalid invite code", "INVALID_INVITE_CODE")
                
                if invite.is_used:
                    raise ValidationError("Invite code has already been used", "INVITE_CODE_USED")
            

                # updating invite
                invite.is_used = True
                invite.updated_at = datetime.now(timezone.utc)

                # creating user.
                user = User(
                    email=email,
                    organisation_id=invite.organisation_id,
                    invite_code_id=invite.id,
                    role=invite.role,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )

                user.set_password(password)
                
                db.session.add(user)
                db.session.commit()
                
            return user
            
        except Exception as e:
            db.session.rollback()
            raise ValidationError("Failed to create user", "DATABASE_ERROR") from e
        
    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        """
        Get a user by their ID.
        Raises ValidationError if user not found.
        """
        user = User.query.get(user_id)
        if not user:
            raise ValidationError("User not found", "USER_NOT_FOUND")
        return user
        
    @staticmethod
    def get_user_by_email(email: str) -> User:
        """
        Get a user by their email.
        Raises ValidationError if user not found.
        """
        user = User.query.filter_by(email=email).first()
        if not user:
            raise ValidationError("User not found", "USER_NOT_FOUND")
        return user
        
 