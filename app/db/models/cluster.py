from app.db import db
from datetime import datetime
from enum import Enum

class ClusterStatus(Enum):
    ACTIVE = "active"
    DELETED = "deleted"

class Cluster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(db.Integer, db.ForeignKey('organisation.id'), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    ram = db.Column(db.Integer, nullable=False)
    cpu = db.Column(db.Integer, nullable=False)
    gpu = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(32), nullable=False, default=ClusterStatus.ACTIVE.value)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Cluster {self.name}>' 