#!/usr/bin/env python3
import sys
import os
from datetime import datetime, timezone
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from app.db import db, init_db
from app.db.models import Organisation, User, InviteCode
from app.services.user_service import UserService

def create_app():
    app = Flask(__name__)
    init_db(app)
    return app

def setup_org(name: str, admin_email: str, admin_password: str):
    """
    Create a new organization and its admin user.
    """
    try:
        # Create organization
        org = Organisation(
            name=name,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.session.add(org)
        db.session.flush()  # Get the org ID

        # Create admin invite code
        invite = InviteCode(
            code='ADMIN_SETUP',
            user_email=admin_email,
            role='admin',
            organisation_id=org.id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),  # Immediate expiry after use
            is_used=False
        )
        db.session.add(invite)
        db.session.flush()

        # Create admin user
        user = User(
            email=admin_email,
            organisation_id=org.id,
            invite_code_id=invite.id,
            role='admin',
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        user.set_password(admin_password)
        
        # Mark invite as used
        invite.is_used = True
        invite.updated_at = datetime.now(timezone.utc)

        db.session.add(user)
        db.session.commit()

        print(f"""
Organization and admin user created successfully!
Organization: {org.name} (ID: {org.id})
Admin User: {user.email} (ID: {user.id})
        """)

    except Exception as e:
        db.session.rollback()
        print(f"Error: {str(e)}")
        sys.exit(1)

def main():
    if len(sys.argv) != 4:
        print("Usage: python setup_org.py <org_name> <admin_email> <admin_password>")
        sys.exit(1)

    org_name = sys.argv[1]
    admin_email = sys.argv[2]
    admin_password = sys.argv[3]

    app = create_app()
    with app.app_context():
        # Check if org already exists
        existing_org = Organisation.query.filter_by(name=org_name).first()
        if existing_org:
            print(f"Error: Organization '{org_name}' already exists")
            sys.exit(1)

        # Check if admin email already exists
        existing_user = User.query.filter_by(email=admin_email).first()
        if existing_user:
            print(f"Error: User with email '{admin_email}' already exists")
            sys.exit(1)

        setup_org(org_name, admin_email, admin_password)

if __name__ == '__main__':
    main() 