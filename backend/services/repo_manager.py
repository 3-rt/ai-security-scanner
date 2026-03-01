from __future__ import annotations

import logging
import os
import re
import shutil
from collections import Counter
from pathlib import Path

import git

from utils.config import settings

logger = logging.getLogger(__name__)

# Mapping of file extensions to CodeQL-supported languages
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".java": "java",
    ".cs": "csharp",
    ".go": "go",
    ".rb": "ruby",
    ".cpp": "cpp",
    ".c": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
}

# Languages that CodeQL supports for security analysis
SUPPORTED_LANGUAGES = {"python", "javascript", "java", "csharp", "go", "ruby", "cpp"}

# Allowed GitHub URL pattern
GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/[a-zA-Z0-9\-_.]+/[a-zA-Z0-9\-_.]+$"
)


def validate_repo_url(url: str) -> bool:
    """Validate that a URL is a proper GitHub repository URL."""
    return bool(GITHUB_URL_PATTERN.match(url))


def extract_repo_name(url: str) -> str:
    """Extract owner/repo from a GitHub URL."""
    parts = url.replace("https://github.com/", "").split("/")
    return f"{parts[0]}/{parts[1]}"


async def clone_repository(repo_url: str, scan_id: str) -> Path:
    """Clone a GitHub repository to a temporary directory.

    Returns the path to the cloned repository.
    Raises RuntimeError on failure.
    """
    if not validate_repo_url(repo_url):
        raise ValueError(f"Invalid GitHub URL: {repo_url}")

    clone_dir = settings.TEMP_DIR / scan_id / "repo"
    clone_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Cloning %s to %s", repo_url, clone_dir)

    try:
        git.Repo.clone_from(
            repo_url,
            str(clone_dir),
            depth=1,  # Shallow clone for speed
            single_branch=True,
        )
    except git.GitCommandError as e:
        raise RuntimeError(f"Failed to clone repository: {e.stderr}") from e

    # Check repo size
    repo_size_mb = _get_dir_size_mb(clone_dir)
    if repo_size_mb > settings.MAX_REPO_SIZE_MB:
        cleanup_scan(scan_id)
        raise ValueError(
            f"Repository too large ({repo_size_mb:.0f}MB). "
            f"Maximum allowed: {settings.MAX_REPO_SIZE_MB}MB"
        )

    return clone_dir


def detect_language(repo_path: Path) -> str:
    """Detect the primary language of a repository by counting file extensions.

    Returns a CodeQL-supported language string.
    Raises ValueError if no supported language is detected.
    """
    counter: Counter[str] = Counter()

    for root, _dirs, files in os.walk(repo_path):
        # Skip hidden directories and common non-source dirs
        if any(
            part.startswith(".") or part in ("node_modules", "venv", "__pycache__", "dist", "build")
            for part in Path(root).parts
        ):
            continue

        for filename in files:
            ext = Path(filename).suffix.lower()
            lang = EXTENSION_TO_LANGUAGE.get(ext)
            if lang:
                counter[lang] += 1

    if not counter:
        raise ValueError("No supported programming language detected in repository")

    primary_language = counter.most_common(1)[0][0]
    logger.info("Detected language: %s (file counts: %s)", primary_language, dict(counter))
    return primary_language


def cleanup_scan(scan_id: str) -> None:
    """Remove all temporary files for a scan."""
    scan_dir = settings.TEMP_DIR / scan_id
    if scan_dir.exists():
        shutil.rmtree(scan_dir, ignore_errors=True)
        logger.info("Cleaned up scan directory: %s", scan_dir)


def _get_dir_size_mb(path: Path) -> float:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)
