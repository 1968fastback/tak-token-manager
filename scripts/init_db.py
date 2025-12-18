#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app')
from app.main import app
from app.database import db

with app.app_context():
    db.create_all()
    print("✅ Database initialized successfully")
