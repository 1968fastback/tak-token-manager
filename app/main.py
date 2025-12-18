from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import secrets
import string

db = SQLAlchemy()

class EnrollmentToken(db.Model):
    __tablename__ = 'enrollment_tokens'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False, index=True)
    token = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    enrolled = db.Column(db.Boolean, default=False)
    certificate_issued_at = db.Column(db.DateTime, nullable=True)
    group_name = db.Column(db.String(255), default='__ANON__')
    package_generated = db.Column(db.Boolean, default=False)
    package_path = db.Column(db.String(512), nullable=True)
    revoked = db.Column(db.Boolean, default=False)
    email = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    @staticmethod
    def generate_token():
        chars = string.ascii_letters + string.digits
        random_part = ''.join(secrets.choice(chars) for _ in range(18))
        return f"Tok{random_part}2024!@"
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        return not self.is_expired() and not self.enrolled and not self.revoked
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'token': self.token,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'enrolled': self.enrolled,
            'group_name': self.group_name,
            'revoked': self.revoked,
            'is_expired': self.is_expired(),
            'time_remaining': str(self.expires_at - datetime.utcnow()) if not self.is_expired() else 'Expired'
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    action = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(255), nullable=True)
    details = db.Column(db.Text, nullable=True)
