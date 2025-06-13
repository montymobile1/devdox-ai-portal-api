FROM python:3.12-alpine

# Install bash and required packages
RUN apk add --no-cache \
    bash \
    gcc \
    musl-dev \
    linux-headers

# Create a non-root user and group
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production

# Copy pyproject.toml first for better Docker layer caching
COPY pyproject.toml .
COPY app/ ./app

# Install dependencies from pyproject.toml
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .


# Copy application code
COPY entrypoint.sh ./entrypoint.sh

# Create migrations directory (will be mounted as volume)
RUN mkdir -p /app/migrations
COPY run_migrations.py ./run_migrations.py
COPY fetch_secrets.py ./fetch_secrets.py

COPY aerich.ini ./aerich.ini
COPY pyproject.toml ./pyproject.toml


# Change ownership of the app directory to the non-root user

RUN chown -R appuser:appgroup /app \
    && chmod +x entrypoint.sh

# Switch to the non-root user (this should be LAST)
USER appuser

ENTRYPOINT ["/bin/bash", "./entrypoint.sh"]