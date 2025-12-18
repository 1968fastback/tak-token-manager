#!/bin/bash
set -e

echo "Starting TAK Token Manager..."

# Wait for database
echo "Waiting for database..."
max_retries=30
retry=0

while ! pg_isready -h db -p 5432 -U takuser > /dev/null 2>&1; do
    retry=$((retry + 1))
    if [ $retry -ge $max_retries ]; then
        echo "Database timeout"
        exit 1
    fi
    sleep 2
done

echo "Database ready"

# Initialize database
echo "Initializing database..."
python /app/scripts/init_db.py || echo "Database may already exist"

# Start cron
echo "Starting cron..."
cron

echo "Starting web server..."
cd /app
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app.main:app
