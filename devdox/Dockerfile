FROM python:3.12-alpine

# Update package index and upgrade sqlite-libs to fix CVE-2025-6965
RUN apk update && apk upgrade sqlite-libs

# Install bash and required packages
RUN apk add --no-cache \
    bash \
    git \
    gcc \
    musl-dev \
    linux-headers \
    build-base

# Create a non-root user and group
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    MIGRATIONS_PATH=/data/migrations
# Copy pyproject.toml first for better Docker layer caching
COPY pyproject.toml .
COPY app ./app

# Install dependencies from pyproject.toml
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .


# Copy application code
COPY entrypoint.sh ./entrypoint.sh

# Create migrations directory (will be mounted as volume)
COPY run_migrations.py ./run_migrations.py
#COPY ../vault-fetcher/fetch_secrets.py ./fetch_secrets.py

COPY aerich.ini ./aerich.ini
COPY pyproject.toml ./pyproject.toml

RUN chmod +x entrypoint.sh

# Change ownership of the app directory to the non-root user
# 🔧 FIX: Change ownership of ALL files to appuser BEFORE switching user
RUN chown -R appuser:appgroup /app
RUN mkdir -p /data/migrations && chown -R appuser:appgroup /data && chmod -R 755 /data && chmod -R 755 /data/migrations


# Switch to the non-root user (this should be LAST)
USER appuser

ENTRYPOINT ["/bin/bash", "./entrypoint.sh"]