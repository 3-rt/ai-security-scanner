# Setup Guide

## Prerequisites

- **Python 3.11+** — Backend runtime
- **Node.js 18+** — Frontend runtime
- **CodeQL CLI** — Static analysis engine
- **Git** — For cloning target repositories
- **Anthropic API Key** (optional) — For AI-enhanced explanations

## 1. Install CodeQL CLI

### macOS (Homebrew)
```bash
brew install codeql
```

### Manual Installation
1. Download the latest release from [github.com/github/codeql-cli-binaries/releases](https://github.com/github/codeql-cli-binaries/releases)
2. Extract and add to your PATH:
```bash
export CODEQL_PATH=/path/to/codeql
```

3. Verify installation:
```bash
codeql version
```

## 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY (optional but recommended)

# Start the server
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

## 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# Default API URL is http://localhost:8000 (no changes needed for local dev)

# Start development server
npm run dev
```

The app will be available at `http://localhost:3000`.

## 4. Test with the Demo App

The `vulnerable-demo-app/` directory contains intentionally vulnerable Python and JavaScript code. To test the scanner:

1. Push `vulnerable-demo-app/` to a public GitHub repository
2. Visit `http://localhost:3000`
3. Enter your repository URL and click "Scan Repository"
4. Watch the progress tracker and review the results

## Environment Variables

### Backend (.env)

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | No | — | Claude API key for AI enhancement |
| `CODEQL_PATH` | No | `codeql` | Path to CodeQL CLI binary |
| `TEMP_DIR` | No | `/tmp/codeql_scans` | Temp directory for cloned repos |
| `MAX_REPO_SIZE_MB` | No | `500` | Max repo size limit |
| `SCAN_TIMEOUT_SECONDS` | No | `600` | CodeQL timeout |

### Frontend (.env.local)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Backend API URL |

## Troubleshooting

**CodeQL not found**: Ensure `codeql` is in your PATH or set `CODEQL_PATH` in `.env`.

**CORS errors**: The backend allows `localhost:3000` by default. If using a different port, update `main.py`.

**AI enhancement skipped**: If no `ANTHROPIC_API_KEY` is set, the scanner still works but provides generic explanations instead of AI-generated ones.

**Scan timeout**: Large repositories may exceed the default 600-second timeout. Increase `SCAN_TIMEOUT_SECONDS` in `.env`.
