#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app')
from app.email_service import EmailService

email_service = EmailService()
if email_service.enabled:
    print("✅ Email service configured")
    print(f"   Server: {email_service.smtp_server}:{email_service.smtp_port}")
    print(f"   From: {email_service.from_email}")
else:
    print("❌ Email service not configured")
    print("   Set SMTP_USER and SMTP_PASSWORD in .env")
