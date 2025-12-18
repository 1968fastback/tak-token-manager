import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_user)
        self.from_name = os.getenv('FROM_NAME', 'TAK Admin')
        self.enabled = bool(self.smtp_user and self.smtp_password)
    
    def send_enrollment_email(self, username, email, token, expires_at, qr_url, package_url):
        if not self.enabled:
            return {'success': False, 'error': 'Email not configured'}
        try:
            msg = MIMEMultipart()
            msg['From'] = f'{self.from_name} <{self.from_email}>'
            msg['To'] = email
            msg['Subject'] = f'TAK Enrollment - {username}'
            body = f"""TAK Server Enrollment

Username: {username}
Password: {token}
Expires: {expires_at}

Download: {package_url}

ShadowMoses Command Center"""
            msg.attach(MIMEText(body, 'plain'))
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            return {'success': True}
        except Exception as e:
            logger.error(f"Email error: {e}")
            return {'success': False, 'error': str(e)}
