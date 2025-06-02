FROM python:3.12-slim

# Create a non-root user and group
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
# Copy application code
COPY app/ ./app
COPY entrypoint.sh ./entrypoint.sh

# Create migrations directory (will be mounted as volume)
RUN mkdir -p /app/migrations
COPY run_migrations.py ./run_migrations.py

COPY aerich.ini ./aerich.ini
COPY pyproject.toml ./pyproject.toml

# Change ownership of the app directory to the non-root user

RUN chown -R appuser:appgroup /app \
    && chmod +x entrypoint.sh

# Switch to the non-root user (this should be LAST)
USER appuser
ENTRYPOINT ["./entrypoint.sh"]
