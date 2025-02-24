from datetime import datetime, timedelta, timezone
import secrets
from app.db.models import InviteCode, User
from app.exceptions import ValidationError
from app.db import db

class InviteService:
    @staticmethod
    def generate_invite_code() -> str:
        # it can collide, maybe add a db call to check if it already is used.

        return secrets.token_urlsafe(16)

    

    @staticmethod
    def create_invite(admin_user: User, email: str, role: str) -> InviteCode:
        
        try:
            if User.query.filter_by(email=email).first():
                raise ValidationError("Email is already registered", "EMAIL_EXISTS")

            with db.session.begin_nested():
                # Check if there's an existing unused invite for this email
                existing_invite = InviteCode.query.filter_by(
                    user_email=email,
                    is_used=False
                ).first()

                if existing_invite:
                    raise ValidationError(
                        "An unused invite code already exists for this email",
                        "INVITE_EXISTS"
                    )

                # Create new invite code
                invite = InviteCode(
                    code=InviteService.generate_invite_code(),
                    user_email=email,
                    role=role,
                    organisation_id=admin_user.organisation_id,
                    created_at=datetime.now(timezone.utc),
                    valid_until=datetime.now(timezone.utc) + timedelta(days=7),  # 7 days validity
                    is_used=False
                )

                db.session.add(invite)

            db.session.commit()
            return invite

        except Exception as e:
            db.session.rollback()
            raise

    @staticmethod
    def list_invites(admin_user: User, include_used: bool = False) -> list[InviteCode]:
        """List all invites for an organization"""
        query = InviteCode.query.filter_by(organisation_id=admin_user.organisation_id)
        
        if not include_used:
            query = query.filter_by(is_used=False)
            
        return query.order_by(InviteCode.created_at.desc()).all()