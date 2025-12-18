#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app')
from app.main import app
from app.token_service import TokenService
from datetime import datetime

with app.app_context():
    result = TokenService.cleanup_expired_tokens()
    print(f"[{datetime.now()}] Cleaned up {result['deleted_count']} expired tokens")
