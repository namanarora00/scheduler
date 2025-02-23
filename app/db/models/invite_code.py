from app.db import db
from datetime import datetime

class InviteCode(db.Model):   
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(128), unique=True, nullable=False)
    
    organisation_id = db.Column(db.Integer, db.ForeignKey('organisation.id'), nullable=False)
    
    role = db.Column(db.String(128), nullable=False)
    user_email = db.Column(db.String(128), nullable=True)

    valid_until = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


    def __repr__(self):
        return f'<InviteCode {self.code}>' 