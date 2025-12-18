FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    zip \
    openssh-client \
    cron \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY config/ ./config/

# Make scripts executable
RUN chmod +x scripts/*.py scripts/*.sh || true

# Create directories
RUN mkdir -p /app/data /app/packages /app/logs

# Setup cron for token cleanup
RUN echo "*/5 * * * * cd /app && python scripts/cleanup_tokens.py >> /app/logs/cleanup.log 2>&1" > /etc/cron.d/token-cleanup
RUN chmod 0644 /etc/cron.d/token-cleanup
RUN crontab /etc/cron.d/token-cleanup

# Expose port
EXPOSE 5000

# Copy entrypoint
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
