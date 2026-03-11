# AI Security Scanner

Automated security vulnerability scanner for GitHub repositories. Combines [Semgrep](https://semgrep.dev/) static analysis with [Claude AI](https://www.anthropic.com/) to produce actionable security reports with explanations, attack scenarios, and fix suggestions.

## How It Works

```
GitHub URL → Shallow Clone → Semgrep Analysis → SARIF Parse → AI Enhancement → Report
```

1. **Clone** — Shallow-clones the target repository (`depth=1`)
2. **Detect Language** — Counts file extensions to select focused Semgrep rulesets
3. **Analyze** — Runs Semgrep with language-specific + OWASP rules, outputs SARIF
4. **Parse** — Extracts vulnerabilities from SARIF, maps severity, elevates critical patterns (SQLi, command injection, etc.)
5. **AI Enhance** — Sends each finding to Claude in parallel for explanation, attack scenario, fixed code, business impact, and confidence scoring

## Architecture

```
Frontend (Next.js 14 / Vercel)
  ├── POST /api/scan             → starts scan, returns scan_id
  ├── GET  /api/scan/{id}/status → polls progress (2s interval)
  └── GET  /api/scan/{id}/results→ fetches enriched vulnerabilities

Backend (FastAPI / Railway)
  ├── routers/scan.py            → API endpoints, in-memory scan state
  ├── services/repo_manager.py   → git clone, language detection, cleanup
  ├── services/semgrep_runner.py → runs Semgrep CLI, outputs SARIF
  ├── services/sarif_parser.py   → SARIF → Vulnerability objects
  ├── services/ai_enhancer.py    → Claude API enhancement (parallel)
  └── utils/config.py            → environment configuration
```

## Supported Languages

| Language   | Semgrep Rulesets                          |
|------------|-------------------------------------------|
| Python     | `p/python`, `p/flask`, `p/django`, `p/owasp-top-ten` |
| JavaScript | `p/javascript`, `p/nodejs`, `p/owasp-top-ten`        |
| Java       | `p/java`, `p/owasp-top-ten`                          |
| Go         | `p/golang`, `p/owasp-top-ten`                        |
| Ruby       | `p/ruby`, `p/owasp-top-ten`                          |
| PHP        | `p/php`, `p/owasp-top-ten`                           |
| Other      | `p/owasp-top-ten`, `p/security-audit`                |

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- [Semgrep CLI](https://semgrep.dev/docs/getting-started/)
- [Anthropic API key](https://console.anthropic.com/) (optional — scanner works without it)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install Semgrep
pip install semgrep
# or: brew install semgrep

# Configure environment
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY

# Run
uvicorn main:app --reload --port 8000
```

#### Environment Variables

| Variable               | Default                  | Description                          |
|------------------------|--------------------------|--------------------------------------|
| `ANTHROPIC_API_KEY`    | *(empty)*                | Claude API key for AI enhancement    |
| `TEMP_DIR`             | `/tmp/security_scans`    | Directory for cloned repos and SARIF |
| `MAX_REPO_SIZE_MB`     | `500`                    | Maximum repository size allowed      |
| `SCAN_TIMEOUT_SECONDS` | `600`                    | Semgrep execution timeout            |

### Frontend

```bash
cd frontend
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local to point to your backend

# Run
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## API Reference

### `POST /api/scan`

Start a new security scan.

**Request:**
```json
{ "repo_url": "https://github.com/owner/repo" }
```

**Response:**
```json
{
  "scan_id": "a1b2c3d4e5f6",
  "status": "started",
  "message": "Scan initiated successfully"
}
```

### `GET /api/scan/{scan_id}/status`

Poll scan progress.

**Response:**
```json
{
  "scan_id": "a1b2c3d4e5f6",
  "status": "running",
  "progress": 55,
  "current_step": "Running Semgrep security scan",
  "steps_completed": ["clone_repo", "detect_language"],
  "steps_remaining": ["analyze", "parse_results", "ai_enhance"],
  "error": null
}
```

Status values: `pending`, `running`, `complete`, `failed`.

### `GET /api/scan/{scan_id}/results`

Get completed scan results.

**Response:**
```json
{
  "scan_id": "a1b2c3d4e5f6",
  "repo_url": "https://github.com/owner/repo",
  "repo_name": "owner/repo",
  "scanned_at": "2025-01-15T12:00:00Z",
  "language": "python",
  "summary": {
    "total": 5,
    "critical": 1,
    "high": 2,
    "medium": 1,
    "low": 1
  },
  "vulnerabilities": [
    {
      "id": "vuln_001",
      "title": "SQL Injection via string concatenation",
      "severity": "critical",
      "scanner_severity": "high",
      "file": "app/db.py",
      "line": 42,
      "rule_id": "python.lang.security.audit.formatted-sql-query",
      "vulnerable_code": "query = f\"SELECT * FROM users WHERE id = {user_id}\"",
      "fixed_code": "query = \"SELECT * FROM users WHERE id = %s\"\ncursor.execute(query, (user_id,))",
      "ai_explanation": "This code builds a SQL query using an f-string with user input...",
      "attack_scenario": "1. Attacker submits user_id = '1 OR 1=1'...",
      "business_impact": "Full database compromise including user credentials and PII.",
      "fix_time_estimate": "15 minutes",
      "confidence": 0.95,
      "false_positive_likelihood": 0.05
    }
  ]
}
```

### `GET /health`

Health check. Returns Semgrep installation status and version.

## Security Controls

- **GitHub URL validation** — only `https://github.com/{owner}/{repo}` accepted (SSRF defense)
- **Path traversal defense** — code snippets validated against repo root
- **Repository size limits** — configurable max size (default 500 MB)
- **Scan timeout** — configurable timeout (default 600s)
- **Rate limiting** — via slowapi
- **Temp file cleanup** — cloned repos deleted after scan completes
- **Fallback mode** — scanner works without Anthropic API key (basic explanations only)

## Deployment

### Backend (Railway)

The backend deploys via Docker on Railway. See `backend/Dockerfile` and `backend/railway.toml`.

Set the `ANTHROPIC_API_KEY` environment variable in Railway's dashboard.

### Frontend (Vercel)

The frontend deploys on Vercel. Set `NEXT_PUBLIC_API_URL` to your Railway backend URL.

## Design Decisions

- **Semgrep over CodeQL** — lower memory footprint, better suited for Railway's container limits
- **Parallel AI enhancement** — all findings sent to Claude concurrently for lower latency
- **Shallow clone** — `depth=1` for faster cloning, sufficient for static analysis
- **In-memory scan state** — simple for single-instance deployment; scans are ephemeral
- **Severity elevation** — known dangerous patterns (SQLi, command injection) auto-elevated to critical regardless of scanner output

## Tech Stack

| Layer    | Technology                                    |
|----------|-----------------------------------------------|
| Frontend | Next.js 14, React 18, Tailwind CSS, Vercel Analytics |
| Backend  | FastAPI, Pydantic, uvicorn, slowapi           |
| Scanner  | Semgrep CLI (SARIF output)                    |
| AI       | Claude API (claude-sonnet-4-20250514)             |
| Deploy   | Railway (backend), Vercel (frontend)          |
