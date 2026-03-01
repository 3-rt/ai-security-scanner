# Architecture Overview

## System Design

```
┌─────────────────────────────────────────────────────────┐
│                     Next.js Frontend                    │
│                                                         │
│  ┌──────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │ ScanForm │→ │ ProgressTracker │→ │ Results Page   │  │
│  │          │  │ (polls /status) │  │ + VulnCards    │  │
│  └──────────┘  └─────────────────┘  │ + CodeDiff     │  │
│                                     └────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (REST API)
┌──────────────────────▼───────────────────────────────────┐
│                    FastAPI Backend                       │
│                                                          │
│  POST /api/scan ──→ Background Task Pipeline:            │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │ RepoManager  │→ │ CodeQL       │→ │ SARIF Parser  │   │
│  │ (git clone)  │  │ Runner       │  │               │   │
│  └──────────────┘  └──────────────┘  └───────┬───────┘   │
│                                              │           │
│                                     ┌────────▼────────┐  │
│                                     │  AI Enhancer    │  │
│                                     │  (Claude API)   │  │
│                                     └─────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Data Flow

1. **User submits URL** → `POST /api/scan` → returns `scan_id`
2. **Background pipeline starts:**
   - `RepoManager` clones the repo (shallow, depth=1)
   - `RepoManager` detects primary language via file extension analysis
   - `CodeQLRunner` creates a CodeQL database from the source
   - `CodeQLRunner` runs the language-appropriate security query suite
   - `SARIFParser` parses the SARIF v2.1.0 output into structured data
   - `AIEnhancer` sends each finding to Claude for explanation and fix generation
3. **Frontend polls** `GET /api/scan/{id}/status` every 2 seconds
4. **On completion** → `GET /api/scan/{id}/results` returns enhanced findings

## Key Components

### Backend

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI app, CORS, rate limiting |
| `routers/scan.py` | API endpoints, scan orchestration, in-memory state |
| `services/repo_manager.py` | Git operations, language detection, cleanup |
| `services/codeql_runner.py` | CodeQL database creation and analysis |
| `services/sarif_parser.py` | SARIF JSON parsing, severity mapping |
| `services/ai_enhancer.py` | Claude API integration, prompt engineering |
| `models/schemas.py` | Pydantic models for request/response validation |
| `utils/config.py` | Environment variable management |

### Frontend

| Component | Purpose |
|---|---|
| `ScanForm` | URL input with validation, triggers scan |
| `ProgressTracker` | Real-time progress polling with step indicators |
| `VulnerabilityCard` | Expandable card with AI explanation and code diff |
| `CodeDiff` | Side-by-side code viewer with syntax highlighting |
| `SeverityBadge` | Color-coded severity indicator |
| `SummaryStats` | Overview statistics cards |

## Design Decisions

**In-memory state**: Scan state is stored in a Python dict. This avoids database setup complexity and is sufficient for a demo tool. Trade-off: scans are lost on server restart.

**Shallow clone**: Repos are cloned with `depth=1` for speed. Full history isn't needed for static analysis.

**Async pipeline**: The scan runs as a background `asyncio.create_task`, so the API remains responsive. The frontend polls for updates.

**Fallback AI**: If no Anthropic API key is configured, the scanner still functions with rule-based explanations. This ensures the tool works without paid API access.

**Severity upgrade**: CodeQL's severity levels (error/warning/note) are mapped to our scale (critical/high/medium/low). Known dangerous rules (SQL injection, command injection) are automatically upgraded to "critical".

## Security Considerations

- URL validation prevents SSRF (only `https://github.com/` URLs accepted)
- File path validation in SARIF parser prevents directory traversal
- Repo size limits prevent disk exhaustion
- Scan timeout prevents runaway processes
- CORS restricted to `localhost:3000`
- Rate limiting via `slowapi`
- Temp files cleaned up after each scan
