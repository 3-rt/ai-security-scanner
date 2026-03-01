from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from models.schemas import (
    ScanRequest,
    ScanResponse,
    ScanResultsResponse,
    ScanStatus,
    ScanStatusResponse,
    ScanStep,
    ScanSummary,
    STEP_LABELS,
    STEP_WEIGHTS,
    Vulnerability,
)
from services import repo_manager, codeql_runner, sarif_parser, ai_enhancer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# In-memory scan state store
scans: dict[str, dict[str, Any]] = {}

ALL_STEPS = list(ScanStep)


def _compute_progress(completed_steps: list[ScanStep]) -> int:
    """Compute overall progress percentage from completed steps."""
    total_weight = sum(STEP_WEIGHTS.values())
    completed_weight = sum(STEP_WEIGHTS[s] for s in completed_steps)
    return int((completed_weight / total_weight) * 100)


@router.post("/scan", response_model=ScanResponse)
async def initiate_scan(request: ScanRequest) -> ScanResponse:
    """Start a new security scan on a GitHub repository."""
    scan_id = uuid.uuid4().hex[:12]

    scans[scan_id] = {
        "status": ScanStatus.PENDING,
        "progress": 0,
        "current_step": "",
        "steps_completed": [],
        "steps_remaining": [s.value for s in ALL_STEPS],
        "repo_url": request.repo_url,
        "repo_name": repo_manager.extract_repo_name(request.repo_url),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "language": "",
        "vulnerabilities": [],
        "error": None,
    }

    # Launch background scan task
    asyncio.create_task(_run_scan(scan_id, request.repo_url))

    return ScanResponse(
        scan_id=scan_id,
        status="started",
        message="Scan initiated successfully",
    )


@router.get("/scan/{scan_id}/status", response_model=ScanStatusResponse)
async def get_scan_status(scan_id: str) -> ScanStatusResponse:
    """Get the current status of a scan."""
    scan = scans.get(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return ScanStatusResponse(
        scan_id=scan_id,
        status=scan["status"],
        progress=scan["progress"],
        current_step=scan["current_step"],
        steps_completed=scan["steps_completed"],
        steps_remaining=scan["steps_remaining"],
        error=scan.get("error"),
    )


@router.get("/scan/{scan_id}/results", response_model=ScanResultsResponse)
async def get_scan_results(scan_id: str) -> ScanResultsResponse:
    """Get the results of a completed scan."""
    scan = scans.get(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan["status"] == ScanStatus.RUNNING:
        raise HTTPException(status_code=202, detail="Scan still in progress")

    if scan["status"] == ScanStatus.FAILED:
        raise HTTPException(status_code=500, detail=scan.get("error", "Scan failed"))

    vulns: list[Vulnerability] = scan.get("vulnerabilities", [])
    summary = _compute_summary(vulns)

    return ScanResultsResponse(
        scan_id=scan_id,
        repo_url=scan["repo_url"],
        repo_name=scan["repo_name"],
        scanned_at=scan["started_at"],
        language=scan.get("language", "unknown"),
        summary=summary,
        vulnerabilities=vulns,
    )


def _compute_summary(vulns: list[Vulnerability]) -> ScanSummary:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for v in vulns:
        sev = v.severity.lower()
        if sev in counts:
            counts[sev] += 1
    return ScanSummary(total=len(vulns), **counts)


def _mark_step(scan_id: str, step: ScanStep) -> None:
    """Mark a step as the current step and update progress."""
    scan = scans[scan_id]
    scan["status"] = ScanStatus.RUNNING
    scan["current_step"] = STEP_LABELS[step]

    completed = [s for s in ALL_STEPS if s.value in scan["steps_completed"]]
    scan["progress"] = _compute_progress(completed)
    scan["steps_remaining"] = [
        s.value for s in ALL_STEPS if s.value not in scan["steps_completed"]
    ]


def _complete_step(scan_id: str, step: ScanStep) -> None:
    """Mark a step as completed."""
    scan = scans[scan_id]
    if step.value not in scan["steps_completed"]:
        scan["steps_completed"].append(step.value)

    completed = [s for s in ALL_STEPS if s.value in scan["steps_completed"]]
    scan["progress"] = _compute_progress(completed)
    scan["steps_remaining"] = [
        s.value for s in ALL_STEPS if s.value not in scan["steps_completed"]
    ]


async def _run_scan(scan_id: str, repo_url: str) -> None:
    """Execute the full scan pipeline in the background."""
    try:
        # Step 1: Clone repository
        _mark_step(scan_id, ScanStep.CLONE_REPO)
        repo_path = await repo_manager.clone_repository(repo_url, scan_id)
        _complete_step(scan_id, ScanStep.CLONE_REPO)

        # Step 2: Detect language
        _mark_step(scan_id, ScanStep.DETECT_LANGUAGE)
        language = repo_manager.detect_language(repo_path)
        scans[scan_id]["language"] = language
        _complete_step(scan_id, ScanStep.DETECT_LANGUAGE)

        # Step 3: Create CodeQL database
        _mark_step(scan_id, ScanStep.CREATE_DATABASE)
        db_path = await codeql_runner.create_database(repo_path, language, scan_id)
        _complete_step(scan_id, ScanStep.CREATE_DATABASE)

        # Step 4: Run analysis
        _mark_step(scan_id, ScanStep.ANALYZE)
        sarif_path = await codeql_runner.run_analysis(db_path, language, scan_id)
        _complete_step(scan_id, ScanStep.ANALYZE)

        # Step 5: Parse SARIF results
        _mark_step(scan_id, ScanStep.PARSE_RESULTS)
        vulnerabilities = sarif_parser.parse_sarif(sarif_path, repo_path)
        _complete_step(scan_id, ScanStep.PARSE_RESULTS)

        # Step 6: AI enhancement
        _mark_step(scan_id, ScanStep.AI_ENHANCE)
        enhanced = await ai_enhancer.enhance_vulnerabilities(vulnerabilities)
        _complete_step(scan_id, ScanStep.AI_ENHANCE)

        # Done
        scans[scan_id]["vulnerabilities"] = enhanced
        scans[scan_id]["status"] = ScanStatus.COMPLETE
        scans[scan_id]["progress"] = 100
        scans[scan_id]["current_step"] = "Scan complete"
        scans[scan_id]["steps_remaining"] = []

        logger.info(
            "Scan %s complete: %d vulnerabilities found", scan_id, len(enhanced)
        )

    except Exception as e:
        logger.exception("Scan %s failed", scan_id)
        scans[scan_id]["status"] = ScanStatus.FAILED
        scans[scan_id]["error"] = str(e)
        scans[scan_id]["current_step"] = f"Failed: {e}"

    finally:
        # Clean up cloned repo (keep results in memory)
        repo_manager.cleanup_scan(scan_id)
