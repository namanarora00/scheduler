from app.db.models import Organisation
from app.exceptions import ValidationError


class OrgService:   
   
    @staticmethod
    def get_organisation(org_id: int) -> Organisation:
        """Get organization by ID"""
        org = Organisation.query.get(org_id)
        if not org:
            raise ValidationError("Organization not found", "ORG_NOT_FOUND")
        return org
