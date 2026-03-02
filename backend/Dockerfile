FROM python:3.12-slim

# System deps: git (for gitpython), curl (for semgrep install)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Semgrep via standalone installer (more reliable than pip)
RUN python3 -m pip install --no-cache-dir semgrep \
    && semgrep --version

# App setup
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV TEMP_DIR=/tmp/security_scans

EXPOSE 8000

# Railway injects $PORT at runtime; fall back to 8000 locally
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
