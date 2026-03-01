from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from models.schemas import Vulnerability
from utils.config import settings

logger = logging.getLogger(__name__)

ENHANCEMENT_PROMPT = """\
You are a senior application security engineer. Analyze the following vulnerability found by CodeQL static analysis and provide a detailed, actionable assessment.

## Vulnerability Details
- **Rule ID:** {rule_id}
- **Title:** {title}
- **Severity (CodeQL):** {codeql_severity}
- **File:** {file}
- **Line:** {line}

## Vulnerable Code
```
{vulnerable_code}
```

Respond with a JSON object containing exactly these fields:
{{
  "ai_explanation": "A clear, plain-English explanation of what the vulnerability is and why the code is insecure. 2-3 sentences aimed at a developer who may not be a security expert.",
  "attack_scenario": "A step-by-step realistic attack scenario showing how an attacker could exploit this vulnerability. Use numbered steps.",
  "fixed_code": "The corrected version of the vulnerable code snippet. Show only the fixed code, not the entire file.",
  "business_impact": "One sentence describing the potential business impact if this vulnerability is exploited.",
  "fix_time_estimate": "Estimated time to fix (e.g., '5 minutes', '30 minutes', '2 hours').",
  "severity": "Your assessed severity: 'critical', 'high', 'medium', or 'low'. May differ from CodeQL's assessment.",
  "confidence": 0.95,
  "false_positive_likelihood": 0.05
}}

Important: Return ONLY valid JSON. No markdown code fences, no extra text.
"""


async def enhance_vulnerabilities(
    vulnerabilities: list[Vulnerability],
) -> list[Vulnerability]:
    """Enhance a list of vulnerabilities with AI-generated analysis.

    Uses Claude API to generate explanations, attack scenarios, and fixes.
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("No Anthropic API key configured; skipping AI enhancement")
        return _apply_fallback_enhancements(vulnerabilities)

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    enhanced: list[Vulnerability] = []

    for vuln in vulnerabilities:
        try:
            result = await _enhance_single(client, vuln)
            enhanced.append(result)
        except Exception as e:
            logger.error("AI enhancement failed for %s: %s", vuln.id, e)
            enhanced.append(_apply_single_fallback(vuln))

    return enhanced


async def _enhance_single(
    client: anthropic.AsyncAnthropic, vuln: Vulnerability
) -> Vulnerability:
    """Enhance a single vulnerability with Claude API."""
    prompt = ENHANCEMENT_PROMPT.format(
        rule_id=vuln.rule_id,
        title=vuln.title,
        codeql_severity=vuln.codeql_severity,
        file=vuln.file,
        line=vuln.line,
        vulnerable_code=vuln.vulnerable_code or "(code snippet not available)",
    )

    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    data = _parse_ai_response(response_text)

    return Vulnerability(
        id=vuln.id,
        title=vuln.title,
        severity=data.get("severity", vuln.severity),
        codeql_severity=vuln.codeql_severity,
        file=vuln.file,
        line=vuln.line,
        end_line=vuln.end_line,
        rule_id=vuln.rule_id,
        vulnerable_code=vuln.vulnerable_code,
        fixed_code=data.get("fixed_code", ""),
        ai_explanation=data.get("ai_explanation", ""),
        attack_scenario=data.get("attack_scenario", ""),
        business_impact=data.get("business_impact", ""),
        fix_time_estimate=data.get("fix_time_estimate", ""),
        confidence=data.get("confidence", 0.8),
        false_positive_likelihood=data.get("false_positive_likelihood", 0.1),
    )


def _parse_ai_response(text: str) -> dict[str, Any]:
    """Parse JSON response from Claude, handling edge cases."""
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

    logger.warning("Could not parse AI response as JSON")
    return {}


def _apply_fallback_enhancements(
    vulnerabilities: list[Vulnerability],
) -> list[Vulnerability]:
    """Apply basic enhancement without AI when API key is unavailable."""
    return [_apply_single_fallback(v) for v in vulnerabilities]


def _apply_single_fallback(vuln: Vulnerability) -> Vulnerability:
    """Generate a basic enhancement for a single vulnerability without AI."""
    explanations: dict[str, str] = {
        "sql-injection": (
            "This code constructs SQL queries using string concatenation or "
            "interpolation with user input, allowing attackers to inject "
            "malicious SQL commands."
        ),
        "command-line-injection": (
            "This code passes user-controlled input to a system command, "
            "allowing attackers to execute arbitrary commands on the server."
        ),
        "code-injection": (
            "This code evaluates user-controlled input as code, allowing "
            "attackers to execute arbitrary code in the application context."
        ),
        "path-injection": (
            "This code uses user-controlled input in file paths without "
            "validation, allowing attackers to read or write arbitrary files."
        ),
        "xss": (
            "This code includes user input in HTML output without proper "
            "escaping, allowing attackers to inject malicious scripts."
        ),
    }

    explanation = "Security vulnerability detected by CodeQL static analysis."
    for pattern, desc in explanations.items():
        if pattern in vuln.rule_id.lower():
            explanation = desc
            break

    return Vulnerability(
        id=vuln.id,
        title=vuln.title,
        severity=vuln.severity,
        codeql_severity=vuln.codeql_severity,
        file=vuln.file,
        line=vuln.line,
        end_line=vuln.end_line,
        rule_id=vuln.rule_id,
        vulnerable_code=vuln.vulnerable_code,
        fixed_code="(AI enhancement unavailable — set ANTHROPIC_API_KEY for detailed fixes)",
        ai_explanation=explanation,
        attack_scenario="(AI enhancement unavailable — set ANTHROPIC_API_KEY for attack scenarios)",
        business_impact="Potential security breach if exploited.",
        fix_time_estimate="Varies",
        confidence=0.7,
        false_positive_likelihood=0.2,
    )
