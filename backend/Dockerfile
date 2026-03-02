FROM python:3.13-slim

# System deps: git (for gitpython)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# App setup
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verify semgrep is installed and working
RUN semgrep --version

COPY . .

ENV TEMP_DIR=/tmp/security_scans

EXPOSE 8000

# Railway injects $PORT at runtime; fall back to 8000 locally
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
