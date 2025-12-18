#!/bin/bash
set -e

echo "
# Wait for database
echo "while ! pg_isready -h db -p 5432 -U takuser > /dev/null 2>&1; do
    sleep 2
done
echo "
# Initialize database
python /app/scripts/init_db.py

# Start cron
cron

echo "cd /app
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app.main:app
