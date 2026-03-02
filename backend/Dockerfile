FROM python:3.13-slim

# System deps: git (for gitpython), wget + unzip (for CodeQL install)
RUN apt-get update && apt-get install -y \
    git \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install CodeQL CLI
ENV CODEQL_VERSION=2.24.2
RUN wget -q https://github.com/github/codeql-cli-binaries/releases/download/v${CODEQL_VERSION}/codeql-linux64.zip \
    && unzip -q codeql-linux64.zip -d /opt \
    && rm codeql-linux64.zip
ENV CODEQL_PATH=/opt/codeql/codeql

# App setup
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Force cache bust: v2
ENV TEMP_DIR=/tmp/codeql_scans

EXPOSE 8000

# Railway injects $PORT at runtime; fall back to 8000 locally
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
