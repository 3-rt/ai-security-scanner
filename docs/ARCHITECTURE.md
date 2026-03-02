# Architecture Overview

## System Design

```
┌─────────────────────────────────────────────────────────┐
│                  Next.js Frontend (Vercel)               │
│                                                         │
│  ┌──────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │ ScanForm │→ │ ProgressTracker │→ │ Results Page   │  │
│  │          │  │ (polls /status) │  │ + VulnCards    │  │
│  └──────────┘  └─────────────────┘  │ + CodeDiff     │  │
│                                     └────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS (REST API)
┌──────────────────────▼───────────────────────────────────┐
│                FastAPI Backend (Railway)                  │
│                                                          │
│  POST /api/scan ──→ Background Task Pipeline:            │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │ RepoManager  │→ │ CodeQL       │→ │ SARIF Parser  │   │
│  │ (git clone)  │  │ Runner       │  │ (merge)       │   │
│  └──────────────┘  └──────────────┘  └───────┬───────┘   │
│                                              │           │
│                                     ┌────────▼────────┐  │
│                                     │  AI Enhancer    │  │
│                                     │ (Claude, async) │  │
│                                     └─────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Data Flow

1. **User submits URL** → `POST /api/scan` → returns `scan_id`
2. **Background pipeline starts:**
   - `RepoManager` shallow-clones the repo (`depth=1`)
   - `RepoManager` detects primary language via file extension counting
   - `CodeQLRunner` creates a CodeQL database (`--ram=512 --threads=1`)
   - `CodeQLRunner` runs 5 targeted security queries **individually** to stay within 1GB RAM, then merges SARIF outputs
   - `SARIFParser` parses the merged SARIF v2.1.0 output into structured data
   - `AIEnhancer` sends all findings to Claude **in parallel** (`asyncio.gather`) for explanation, attack scenarios, and fix generation
3. **Frontend polls** `GET /api/scan/{id}/status` every 2 seconds
4. **On completion** → `GET /api/scan/{id}/results` returns enhanced findings

## Key Components

### Backend

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI app, CORS (allow all origins), rate limiting, health check with CodeQL diagnostics |
| `routers/scan.py` | API endpoints, scan orchestration, in-memory state |
| `services/repo_manager.py` | Git operations, language detection, repo size validation, cleanup |
| `services/codeql_runner.py` | Per-query CodeQL execution, SARIF merging, memory-constrained analysis |
| `services/sarif_parser.py` | SARIF JSON parsing, severity mapping, code snippet extraction |
| `services/ai_enhancer.py` | Parallel Claude API calls, structured prompt engineering, fallback mode |
| `models/schemas.py` | Pydantic models for request/response validation |
| `utils/config.py` | Environment variable management |

### Frontend

| Component | Purpose |
|---|---|
| `ScanForm` | URL input with GitHub validation, triggers scan |
| `ProgressTracker` | Real-time progress polling with animated step indicators |
| `VulnerabilityCard` | Expandable card with AI explanation, attack scenario, and code diff |
| `CodeDiff` | Side-by-side / single code viewer with syntax highlighting and copy button |
| `SeverityBadge` | Color-coded severity indicator (critical/high/medium/low) |
| `SummaryStats` | Overview statistics cards with severity breakdown |

## Design Decisions

**Individual query execution**: Instead of running a full CodeQL query suite (which loads all queries into memory at once), queries are executed one at a time with `--ram=512`. This allows CodeQL to run within Railway's 1GB memory limit. Results are merged into a single SARIF file afterward.

**Parallel AI enhancement**: All vulnerability findings are sent to Claude simultaneously via `asyncio.gather`, reducing the AI enhancement step from O(n) sequential API calls to a single parallel batch.

**In-memory state**: Scan state is stored in a Python dict. This avoids database setup complexity and is sufficient for a demo tool. Trade-off: scans are lost on server restart.

**Shallow clone**: Repos are cloned with `depth=1` for speed. Full history isn't needed for static analysis.

**Async pipeline**: The scan runs as a background `asyncio.create_task`, so the API returns immediately and remains responsive. The frontend polls for updates.

**Fallback AI**: If no Anthropic API key is configured, the scanner still functions with rule-based explanations. This ensures the tool works without paid API access.

**Severity upgrade**: CodeQL's severity levels (error/warning/note) are mapped to our scale (critical/high/medium/low). Known dangerous rules (SQL injection, command injection) are automatically upgraded to "critical".

## Deployment Architecture

| Service | Platform | Configuration |
|---|---|---|
| Frontend | Vercel | Root directory: `frontend`, auto-detected as Next.js |
| Backend | Railway | Root directory: `backend`, Dockerfile build with CodeQL CLI |

The backend Dockerfile installs CodeQL CLI v2.24.2, git, and Python dependencies. The frontend's `next.config.mjs` provides a fallback API URL pointing to the Railway backend.

## Security Considerations

- URL validation prevents SSRF (only `https://github.com/` URLs accepted)
- File path validation in SARIF parser prevents directory traversal
- Repo size limits prevent disk exhaustion (default 500MB)
- Scan timeout prevents runaway processes (default 600s)
- CORS configured with wildcard for deployment flexibility
- Rate limiting via `slowapi`
- Temp files cleaned up after each scan
- Shallow clones minimize disk usage

## Supported Security Queries

| Category | Python | JavaScript | Java |
|---|---|---|---|
| SQL Injection | CWE-089 | CWE-089 | CWE-089 |
| Command Injection | CWE-078 | CWE-078 | CWE-078 |
| Cross-Site Scripting | CWE-079 | CWE-079 | CWE-079 |
| Path Traversal | CWE-022 | CWE-022 | CWE-022 |
| Unsafe Deserialization | CWE-502 | — | CWE-502 |
| Code Injection | — | CWE-094 | — |
