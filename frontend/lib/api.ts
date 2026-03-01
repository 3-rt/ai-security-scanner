function getApiUrl(): string {
  return "https://ai-security-scanner-production.up.railway.app";
}

export interface ScanResponse {
  scan_id: string;
  status: string;
  message: string;
}

export interface ScanStatusResponse {
  scan_id: string;
  status: "pending" | "running" | "complete" | "failed";
  progress: number;
  current_step: string;
  steps_completed: string[];
  steps_remaining: string[];
  error: string | null;
}

export interface Vulnerability {
  id: string;
  title: string;
  severity: "critical" | "high" | "medium" | "low";
  codeql_severity: string;
  file: string;
  line: number;
  end_line: number | null;
  rule_id: string;
  vulnerable_code: string;
  fixed_code: string;
  ai_explanation: string;
  attack_scenario: string;
  business_impact: string;
  fix_time_estimate: string;
  confidence: number;
  false_positive_likelihood: number;
}

export interface ScanSummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface ScanResultsResponse {
  scan_id: string;
  repo_url: string;
  repo_name: string;
  scanned_at: string;
  language: string;
  summary: ScanSummary;
  vulnerabilities: Vulnerability[];
}

export async function startScan(repoUrl: string): Promise<ScanResponse> {
  const res = await fetch(`${getApiUrl()}/api/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: repoUrl }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Failed to start scan" }));
    throw new Error(error.detail || "Failed to start scan");
  }

  return res.json();
}

export async function getScanStatus(scanId: string): Promise<ScanStatusResponse> {
  const res = await fetch(`${getApiUrl()}/api/scan/${scanId}/status`);

  if (!res.ok) {
    throw new Error("Failed to get scan status");
  }

  return res.json();
}

export async function getScanResults(scanId: string): Promise<ScanResultsResponse> {
  const res = await fetch(`${getApiUrl()}/api/scan/${scanId}/results`);

  if (!res.ok) {
    if (res.status === 202) {
      throw new Error("Scan still in progress");
    }
    const error = await res.json().catch(() => ({ detail: "Failed to get results" }));
    throw new Error(error.detail || "Failed to get results");
  }

  return res.json();
}
