# API Documentation

Base URL: `http://localhost:8000`

## Health Check

```
GET /health
```

**Response:**
```json
{"status": "healthy"}
```

---

## Start a Scan

```
POST /api/scan
```

**Request Body:**
```json
{
  "repo_url": "https://github.com/owner/repo"
}
```

**Response (200):**
```json
{
  "scan_id": "abc123def456",
  "status": "started",
  "message": "Scan initiated successfully"
}
```

**Errors:**
- `422` — Invalid URL format (must be `https://github.com/owner/repo`)

---

## Get Scan Status

```
GET /api/scan/{scan_id}/status
```

**Response (200):**
```json
{
  "scan_id": "abc123def456",
  "status": "running",
  "progress": 67,
  "current_step": "Running security queries",
  "steps_completed": ["clone_repo", "detect_language", "create_database"],
  "steps_remaining": ["analyze", "parse_results", "ai_enhance"],
  "error": null
}
```

**Status values:** `pending`, `running`, `complete`, `failed`

**Steps (in order):**
1. `clone_repo` — Clone the GitHub repository
2. `detect_language` — Detect primary programming language
3. `create_database` — Create CodeQL analysis database
4. `analyze` — Run CodeQL security queries
5. `parse_results` — Parse SARIF output
6. `ai_enhance` — Generate AI explanations

**Errors:**
- `404` — Scan not found

---

## Get Scan Results

```
GET /api/scan/{scan_id}/results
```

**Response (200):**
```json
{
  "scan_id": "abc123def456",
  "repo_url": "https://github.com/owner/repo",
  "repo_name": "owner/repo",
  "scanned_at": "2025-01-15T10:30:00Z",
  "language": "python",
  "summary": {
    "total": 8,
    "critical": 2,
    "high": 3,
    "medium": 2,
    "low": 1
  },
  "vulnerabilities": [
    {
      "id": "vuln_001",
      "title": "SQL Injection in Authentication",
      "severity": "critical",
      "codeql_severity": "high",
      "file": "app/routes/login.py",
      "line": 23,
      "end_line": 23,
      "rule_id": "py/sql-injection",
      "vulnerable_code": "query = f\"SELECT * FROM users WHERE username='{username}'\"",
      "fixed_code": "query = \"SELECT * FROM users WHERE username=?\"\ncursor.execute(query, (username,))",
      "ai_explanation": "This login endpoint directly interpolates user input into a SQL query...",
      "attack_scenario": "1. Attacker visits /login\n2. Enters username: admin' OR '1'='1 --\n...",
      "business_impact": "Complete authentication bypass leading to unauthorized access",
      "fix_time_estimate": "5 minutes",
      "confidence": 0.98,
      "false_positive_likelihood": 0.02
    }
  ]
}
```

**Errors:**
- `202` — Scan still in progress
- `404` — Scan not found
- `500` — Scan failed (includes error message)
