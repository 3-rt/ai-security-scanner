"use client";

import { useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { getScanResults, type ScanResultsResponse, type Vulnerability } from "@/lib/api";
import ProgressTracker from "@/components/ProgressTracker";
import SummaryStats from "@/components/SummaryStats";
import VulnerabilityCard from "@/components/VulnerabilityCard";
import SeverityBadge from "@/components/SeverityBadge";

type SeverityFilter = "all" | "critical" | "high" | "medium" | "low";

export default function ResultsPage() {
  const params = useParams();
  const scanId = params.scanId as string;

  const [phase, setPhase] = useState<"loading" | "error" | "results">("loading");
  const [results, setResults] = useState<ScanResultsResponse | null>(null);
  const [error, setError] = useState("");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const fetchResults = useCallback(async () => {
    try {
      const data = await getScanResults(scanId);
      setResults(data);
      setPhase("results");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load results");
      setPhase("error");
    }
  }, [scanId]);

  const handleComplete = useCallback(() => {
    fetchResults();
  }, [fetchResults]);

  const handleError = useCallback((msg: string) => {
    setError(msg);
    setPhase("error");
  }, []);

  const filteredVulns = results?.vulnerabilities.filter((v: Vulnerability) => {
    if (severityFilter !== "all" && v.severity !== severityFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        v.title.toLowerCase().includes(q) ||
        v.file.toLowerCase().includes(q) ||
        v.rule_id.toLowerCase().includes(q) ||
        v.ai_explanation.toLowerCase().includes(q)
      );
    }
    return true;
  }) ?? [];

  const generateMarkdownReport = () => {
    if (!results) return;

    const lines = [
      `# Security Scan Report`,
      ``,
      `**Repository:** ${results.repo_name}`,
      `**Scanned:** ${new Date(results.scanned_at).toLocaleString()}`,
      `**Language:** ${results.language}`,
      ``,
      `## Summary`,
      `| Severity | Count |`,
      `|----------|-------|`,
      `| Critical | ${results.summary.critical} |`,
      `| High | ${results.summary.high} |`,
      `| Medium | ${results.summary.medium} |`,
      `| Low | ${results.summary.low} |`,
      `| **Total** | **${results.summary.total}** |`,
      ``,
      `## Vulnerabilities`,
      ``,
    ];

    for (const v of results.vulnerabilities) {
      lines.push(`### ${v.severity.toUpperCase()}: ${v.title}`);
      lines.push(`- **File:** \`${v.file}:${v.line}\``);
      lines.push(`- **Rule:** \`${v.rule_id}\``);
      lines.push(`- **Confidence:** ${Math.round(v.confidence * 100)}%`);
      lines.push(``);
      if (v.ai_explanation) {
        lines.push(`**Explanation:** ${v.ai_explanation}`);
        lines.push(``);
      }
      if (v.attack_scenario) {
        lines.push(`**Attack Scenario:**`);
        lines.push(v.attack_scenario);
        lines.push(``);
      }
      if (v.vulnerable_code) {
        lines.push("**Vulnerable Code:**");
        lines.push("```");
        lines.push(v.vulnerable_code);
        lines.push("```");
        lines.push(``);
      }
      if (v.fixed_code) {
        lines.push("**Fixed Code:**");
        lines.push("```");
        lines.push(v.fixed_code);
        lines.push("```");
        lines.push(``);
      }
      lines.push(`---`);
      lines.push(``);
    }

    const blob = new Blob([lines.join("\n")], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `scan-report-${scanId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (phase === "loading") {
    return (
      <ProgressTracker
        scanId={scanId}
        onComplete={handleComplete}
        onError={handleError}
      />
    );
  }

  if (phase === "error") {
    return (
      <div className="max-w-2xl mx-auto mt-12 px-4">
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-center">
          <svg className="w-12 h-12 text-red-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h2 className="text-xl font-semibold text-red-400 mb-2">Scan Failed</h2>
          <p className="text-gray-400">{error}</p>
          <a href="/" className="inline-block mt-4 px-4 py-2 bg-gray-800 rounded-lg text-sm hover:bg-gray-700 transition-colors">
            Try Again
          </a>
        </div>
      </div>
    );
  }

  if (!results) return null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold">{results.repo_name}</h1>
          <p className="text-sm text-gray-400 mt-1">
            Scanned {new Date(results.scanned_at).toLocaleString()} &middot;{" "}
            {results.language}
          </p>
        </div>
        <button
          onClick={generateMarkdownReport}
          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm hover:bg-gray-700 transition-colors flex items-center gap-2 self-start"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Export Report
        </button>
      </div>

      {/* Summary */}
      <SummaryStats summary={results.summary} />

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mt-8 mb-6">
        <div className="flex gap-2 flex-wrap">
          {(["all", "critical", "high", "medium", "low"] as const).map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                severityFilter === sev
                  ? "bg-gray-700 text-white"
                  : "bg-gray-800/50 text-gray-400 hover:text-gray-200"
              }`}
            >
              {sev === "all" ? "All" : <SeverityBadge severity={sev} />}
            </button>
          ))}
        </div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search vulnerabilities..."
          className="flex-1 px-3 py-1.5 bg-gray-800/50 border border-gray-700 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
        />
      </div>

      {/* Vulnerability list */}
      <div className="space-y-3">
        {filteredVulns.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            {results.vulnerabilities.length === 0
              ? "No vulnerabilities found. The repository looks clean!"
              : "No vulnerabilities match your filters."}
          </div>
        ) : (
          filteredVulns.map((vuln) => (
            <VulnerabilityCard
              key={vuln.id}
              vulnerability={vuln}
              language={results.language}
            />
          ))
        )}
      </div>
    </div>
  );
}
