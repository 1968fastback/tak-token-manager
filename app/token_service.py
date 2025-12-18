from datetime import datetime, timedelta
from app.database import db, EnrollmentToken, AuditLog

class TokenService:
    @staticmethod
    def create_token(username, group_name='__ANON__', expiry_minutes=120, email=None, notes=None):
        existing = EnrollmentToken.query.filter_by(username=username).first()
        if existing and not existing.is_expired():
            return {'success': False, 'error': 'Active token exists'}
        if existing:
            db.session.delete(existing)
        
        token = EnrollmentToken.generate_token()
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        enrollment_token = EnrollmentToken(
            username=username, token=token, expires_at=expires_at,
            group_name=group_name, email=email, notes=notes
        )
        db.session.add(enrollment_token)
        db.session.add(AuditLog(action='TOKEN_CREATED', username=username))
        db.session.commit()
        return {'success': True, 'token_data': enrollment_token.to_dict()}
    
    @staticmethod
    def get_token(username):
        token = EnrollmentToken.query.filter_by(username=username).first()
        return {'success': bool(token), 'token_data': token.to_dict()} if token else {'success': False}
    
    @staticmethod
    def revoke_token(username):
        token = EnrollmentToken.query.filter_by(username=username).first()
        if not token:
            return {'success': False}
        token.revoked = True
        db.session.commit()
        return {'success': True}
    
    @staticmethod
    def cleanup_expired_tokens():
        expired = EnrollmentToken.query.filter(
            EnrollmentToken.expires_at < datetime.utcnow(),
            EnrollmentToken.enrolled == False
        ).all()
        for token in expired:
            db.session.delete(token)
        db.session.commit()
        return {'success': True, 'deleted_count': len(expired)}
    
    @staticmethod
    def get_statistics():
        now = datetime.utcnow()
        return {
            'total': EnrollmentToken.query.count(),
            'active': EnrollmentToken.query.filter(
                EnrollmentToken.expires_at > now, 
                EnrollmentToken.enrolled == False
            ).count(),
            'enrolled': EnrollmentToken.query.filter_by(enrolled=True).count(),
            'expired': EnrollmentToken.query.filter(
                EnrollmentToken.expires_at < now,
                EnrollmentToken.enrolled == False
            ).count(),
            'revoked': EnrollmentToken.query.filter_by(revoked=True).count()
        }
    
    @staticmethod
    def list_tokens(filter_type='all'):
        query = EnrollmentToken.query
        if filter_type == 'active':
            query = query.filter(EnrollmentToken.expires_at > datetime.utcnow())
        tokens = query.order_by(EnrollmentToken.created_at.desc()).all()
        return {'success': True, 'tokens': [t.to_dict() for t in tokens]}
