from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from models.schemas import Vulnerability

logger = logging.getLogger(__name__)

# Map CodeQL severity levels to our severity scale
SEVERITY_MAP: dict[str, str] = {
    "error": "high",
    "warning": "medium",
    "note": "low",
    "none": "low",
}

# Rules that are typically critical severity
CRITICAL_RULES: set[str] = {
    "py/sql-injection",
    "js/sql-injection",
    "py/code-injection",
    "js/code-injection",
    "py/command-line-injection",
    "js/command-line-injection",
    "py/unsafe-deserialization",
    "js/prototype-polluting-assignment",
    "py/path-injection",
    "js/path-injection",
    "java/sql-injection",
    "java/command-line-injection",
}


def parse_sarif(sarif_path: Path, repo_path: Path) -> list[Vulnerability]:
    """Parse a SARIF file and extract vulnerability information.

    Returns a list of Vulnerability objects.
    """
    try:
        with open(sarif_path, "r") as f:
            sarif_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error("Failed to parse SARIF file: %s", e)
        return []

    vulnerabilities: list[Vulnerability] = []
    vuln_counter = 0

    for run in sarif_data.get("runs", []):
        rules = _build_rule_index(run)
        results = run.get("results", [])

        for result in results:
            vuln_counter += 1
            vuln = _parse_result(result, rules, repo_path, vuln_counter)
            if vuln:
                vulnerabilities.append(vuln)

    logger.info("Parsed %d vulnerabilities from SARIF", len(vulnerabilities))
    return vulnerabilities


def _build_rule_index(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build an index of rule ID -> rule metadata from the SARIF run."""
    rules: dict[str, dict[str, Any]] = {}
    tool = run.get("tool", {})
    driver = tool.get("driver", {})

    for rule in driver.get("rules", []):
        rule_id = rule.get("id", "")
        rules[rule_id] = rule

    return rules


def _parse_result(
    result: dict[str, Any],
    rules: dict[str, dict[str, Any]],
    repo_path: Path,
    index: int,
) -> Vulnerability | None:
    """Parse a single SARIF result into a Vulnerability object."""
    rule_id = result.get("ruleId", "unknown")
    rule = rules.get(rule_id, {})

    # Extract severity
    codeql_level = result.get("level", "warning")
    codeql_severity = SEVERITY_MAP.get(codeql_level, "medium")

    # Upgrade to critical for known dangerous rules
    severity = "critical" if rule_id in CRITICAL_RULES else codeql_severity

    # Extract message
    message = result.get("message", {}).get("text", "Security issue detected")

    # Extract title from rule metadata
    title = rule.get("shortDescription", {}).get("text", "")
    if not title:
        title = rule.get("name", message[:80])

    # Extract location info
    locations = result.get("locations", [])
    if not locations:
        return None

    location = locations[0].get("physicalLocation", {})
    artifact = location.get("artifactLocation", {})
    region = location.get("region", {})

    file_path = artifact.get("uri", "unknown")
    # Make path relative to repo root
    if file_path.startswith("file://"):
        file_path = file_path[7:]
    try:
        file_path = str(Path(file_path).relative_to(repo_path))
    except ValueError:
        pass  # Keep as-is if not relative to repo

    line = region.get("startLine", 0)
    end_line = region.get("endLine", line)

    # Try to extract the vulnerable code snippet
    snippet = region.get("snippet", {}).get("text", "")
    if not snippet:
        snippet = _read_code_snippet(repo_path, file_path, line, end_line)

    return Vulnerability(
        id=f"vuln_{index:03d}",
        title=title,
        severity=severity,
        codeql_severity=codeql_severity,
        file=file_path,
        line=line,
        end_line=end_line,
        rule_id=rule_id,
        vulnerable_code=snippet,
    )


def _read_code_snippet(
    repo_path: Path, file_path: str, start_line: int, end_line: int
) -> str:
    """Read a code snippet from the source file."""
    try:
        full_path = repo_path / file_path
        if not full_path.exists():
            return ""

        # Ensure we don't traverse outside repo
        full_path = full_path.resolve()
        if not str(full_path).startswith(str(repo_path.resolve())):
            return ""

        lines = full_path.read_text().splitlines()
        # Provide context: 2 lines before and after
        context_start = max(0, start_line - 3)
        context_end = min(len(lines), end_line + 2)
        return "\n".join(lines[context_start:context_end])
    except Exception as e:
        logger.debug("Could not read snippet from %s: %s", file_path, e)
        return ""
