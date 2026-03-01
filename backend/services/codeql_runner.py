from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from utils.config import settings

logger = logging.getLogger(__name__)

# CodeQL query suites for each language
QUERY_SUITES: dict[str, str] = {
    "python": "codeql/python-queries:codeql-suites/python-security-and-quality.qls",
    "javascript": "codeql/javascript-queries:codeql-suites/javascript-security-and-quality.qls",
    "java": "codeql/java-queries:codeql-suites/java-security-and-quality.qls",
    "csharp": "codeql/csharp-queries:codeql-suites/csharp-security-and-quality.qls",
    "go": "codeql/go-queries:codeql-suites/go-security-and-quality.qls",
    "ruby": "codeql/ruby-queries:codeql-suites/ruby-security-and-quality.qls",
    "cpp": "codeql/cpp-queries:codeql-suites/cpp-security-and-quality.qls",
}


async def create_database(
    repo_path: Path, language: str, scan_id: str
) -> Path:
    """Create a CodeQL database from a repository.

    Returns the path to the created database.
    """
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
        "--threads=0",  # Use all available threads
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
    """Run CodeQL analysis on a database and output SARIF results.

    Returns the path to the SARIF output file.
    """
    sarif_path = settings.TEMP_DIR / scan_id / "results.sarif"
    codeql = settings.CODEQL_PATH

    suite = QUERY_SUITES.get(language)
    if not suite:
        raise ValueError(f"No query suite available for language: {language}")

    cmd = [
        codeql,
        "database",
        "analyze",
        str(db_path),
        suite,
        "--format=sarifv2.1.0",
        f"--output={sarif_path}",
        "--threads=0",
        "--download",
    ]

    logger.info("Running CodeQL analysis: %s", " ".join(cmd))

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
        logger.error("CodeQL analysis failed: %s", error_msg)
        raise RuntimeError(f"CodeQL analysis failed: {error_msg}")

    logger.info("CodeQL analysis complete. Results at %s", sarif_path)
    return sarif_path


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
