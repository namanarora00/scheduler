from app.db import db
from datetime import datetime
from enum import Enum

class DeploymentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    EVICTED = "evicted"
    DELETED = "deleted"

class DeploymentPriority(Enum):
    LOWEST = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    HIGHEST = 5

    @classmethod
    def is_valid(cls, value: int) -> bool:
        return value in [member.value for member in cls]

class Deployment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    cluster_id = db.Column(db.Integer, db.ForeignKey('cluster.id'), nullable=False)
    status = db.Column(db.String(32), nullable=False, default=DeploymentStatus.PENDING.value)
    priority = db.Column(db.Integer, nullable=False, default=DeploymentPriority.MEDIUM.value)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    ram = db.Column(db.Integer, nullable=False)
    cpu = db.Column(db.Integer, nullable=False)
    gpu = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Deployment {self.name}>' 