FROM python:3.11-slim

WORKDIR /app

# Create the instance directory with proper permissions
RUN mkdir -p /app/instance && chmod 755 /app/instance

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY fetch_secrets.py .

CMD ["python", "fetch_secrets.py"]