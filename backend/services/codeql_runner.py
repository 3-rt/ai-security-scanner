from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from utils.config import settings

logger = logging.getLogger(__name__)

# Individual high-value security queries per language (low memory footprint)
SECURITY_QUERIES: dict[str, list[str]] = {
    "python": [
        "codeql/python-queries:Security/CWE-089/SqlInjection.ql",
        "codeql/python-queries:Security/CWE-078/CommandInjection.ql",
        "codeql/python-queries:Security/CWE-079/ReflectedXss.ql",
        "codeql/python-queries:Security/CWE-022/PathInjection.ql",
        "codeql/python-queries:Security/CWE-502/UnsafeDeserialization.ql",
        "codeql/python-queries:Security/CWE-094/CodeInjection.ql",
        "codeql/python-queries:Security/CWE-798/HardcodedCredentials.ql",
        "codeql/python-queries:Security/CWE-918/FullServerSideRequestForgery.ql",
        "codeql/python-queries:Security/CWE-312/CleartextLogging.ql",
        "codeql/python-queries:Security/CWE-611/Xxe.ql",
    ],
    "javascript": [
        "codeql/javascript-queries:Security/CWE-089/SqlInjection.ql",
        "codeql/javascript-queries:Security/CWE-078/CommandInjection.ql",
        "codeql/javascript-queries:Security/CWE-079/ReflectedXss.ql",
        "codeql/javascript-queries:Security/CWE-022/TaintedPath.ql",
        "codeql/javascript-queries:Security/CWE-094/CodeInjection.ql",
        "codeql/javascript-queries:Security/CWE-798/HardcodedCredentials.ql",
        "codeql/javascript-queries:Security/CWE-918/RequestForgery.ql",
        "codeql/javascript-queries:Security/CWE-312/CleartextLogging.ql",
        "codeql/javascript-queries:Security/CWE-327/BrokenCryptoAlgorithm.ql",
        "codeql/javascript-queries:Security/CWE-116/IncompleteSanitization.ql",
    ],
    "java": [
        "codeql/java-queries:Security/CWE-089/SqlTainted.ql",
        "codeql/java-queries:Security/CWE-078/ExecTainted.ql",
        "codeql/java-queries:Security/CWE-079/XSS.ql",
        "codeql/java-queries:Security/CWE-022/TaintedPath.ql",
        "codeql/java-queries:Security/CWE-502/UnsafeDeserialization.ql",
    ],
}


async def create_database(
    repo_path: Path, language: str, scan_id: str
) -> Path:
    """Create a CodeQL database from a repository."""
    db_path = settings.TEMP_DIR / scan_id / "codeql-db"
    codeql = settings.CODEQL_PATH

    cmd = [
        codeql,
        "database",
        "create",
        str(db_path),
        f"--language={language}",
        f"--source-root={repo_path}",
        "--overwrite",
        "--threads=1",
        "--ram=512",
    ]

    logger.info("Creating CodeQL database: %s", " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(
        proc.communicate(), timeout=settings.SCAN_TIMEOUT_SECONDS
    )

    if proc.returncode != 0:
        error_msg = stderr.decode().strip()
        logger.error("CodeQL database creation failed: %s", error_msg)
        raise RuntimeError(f"CodeQL database creation failed: {error_msg}")

    logger.info("CodeQL database created at %s", db_path)
    return db_path


async def run_analysis(
    db_path: Path, language: str, scan_id: str
) -> Path:
    """Run CodeQL analysis one query at a time to stay within memory limits.

    Runs each query individually and merges SARIF results.
    Returns the path to the merged SARIF output file.
    """
    merged_sarif_path = settings.TEMP_DIR / scan_id / "results.sarif"
    codeql = settings.CODEQL_PATH

    queries = SECURITY_QUERIES.get(language)
    if not queries:
        raise ValueError(f"No queries available for language: {language}")

    all_results: list[dict] = []
    all_rules: list[dict] = []
    base_sarif: dict | None = None

    for i, query in enumerate(queries):
        query_sarif = settings.TEMP_DIR / scan_id / f"result_{i}.sarif"
        logger.info("Running query %d/%d: %s", i + 1, len(queries), query)

        cmd = [
            codeql,
            "database",
            "analyze",
            str(db_path),
            query,
            "--format=sarifv2.1.0",
            f"--output={query_sarif}",
            "--threads=1",
            "--ram=512",
            "--download",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=settings.SCAN_TIMEOUT_SECONDS
        )

        if proc.returncode != 0:
            error_msg = stderr.decode().strip()
            # Skip queries that fail (e.g., not found) but log the error
            logger.warning("Query %s failed (skipping): %s", query, error_msg)
            continue

        if not query_sarif.exists():
            continue

        try:
            with open(query_sarif) as f:
                sarif_data = json.load(f)
        except json.JSONDecodeError:
            logger.warning("Failed to parse SARIF for query %s", query)
            continue

        # Use first valid SARIF as the base structure
        if base_sarif is None:
            base_sarif = sarif_data

        for run in sarif_data.get("runs", []):
            all_results.extend(run.get("results", []))
            driver = run.get("tool", {}).get("driver", {})
            all_rules.extend(driver.get("rules", []))

    # Merge all results into a single SARIF file
    if base_sarif is None:
        # No queries succeeded — create a minimal empty SARIF
        base_sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "CodeQL", "rules": []}}, "results": []}],
        }

    if base_sarif.get("runs"):
        # Deduplicate rules by ID
        seen_rules: set[str] = set()
        unique_rules: list[dict] = []
        for rule in all_rules:
            rid = rule.get("id", "")
            if rid not in seen_rules:
                seen_rules.add(rid)
                unique_rules.append(rule)

        base_sarif["runs"][0]["results"] = all_results
        base_sarif["runs"][0].setdefault("tool", {}).setdefault("driver", {})["rules"] = unique_rules

    with open(merged_sarif_path, "w") as f:
        json.dump(base_sarif, f, indent=2)

    logger.info(
        "CodeQL analysis complete. %d results from %d queries. Output: %s",
        len(all_results), len(queries), merged_sarif_path,
    )
    return merged_sarif_path


async def check_codeql_installed() -> bool:
    """Check if CodeQL CLI is installed and accessible."""
    try:
        proc = await asyncio.create_subprocess_exec(
            settings.CODEQL_PATH, "version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        version = stdout.decode().strip()
        logger.info("CodeQL CLI version: %s", version)
        return proc.returncode == 0
    except FileNotFoundError:
        logger.warning("CodeQL CLI not found at %s", settings.CODEQL_PATH)
        return False
