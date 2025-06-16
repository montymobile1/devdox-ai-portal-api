FROM python:3.11-slim

WORKDIR /app

# Create the secrets directory with proper permissions
RUN mkdir -p /app/secrets && chmod 755 /app/secrets

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY fetch_secrets.py .

CMD ["python", "fetch_secrets.py"]