"use client";

import { useEffect, useState, useCallback } from "react";
import { getScanStatus, type ScanStatusResponse } from "@/lib/api";

const STEP_LABELS: Record<string, string> = {
  clone_repo: "Clone repository",
  detect_language: "Detect language",
  create_database: "Create CodeQL database",
  analyze: "Run security queries",
  parse_results: "Parse results",
  ai_enhance: "AI enhancement",
};

const ALL_STEPS = ["clone_repo", "detect_language", "create_database", "analyze", "parse_results", "ai_enhance"];

interface ProgressTrackerProps {
  scanId: string;
  onComplete: () => void;
  onError: (error: string) => void;
}

export default function ProgressTracker({ scanId, onComplete, onError }: ProgressTrackerProps) {
  const [status, setStatus] = useState<ScanStatusResponse | null>(null);

  const pollStatus = useCallback(async () => {
    try {
      const data = await getScanStatus(scanId);
      setStatus(data);

      if (data.status === "complete") {
        onComplete();
        return false; // stop polling
      }
      if (data.status === "failed") {
        onError(data.error || "Scan failed");
        return false;
      }
      return true; // continue polling
    } catch {
      return true; // retry on network error
    }
  }, [scanId, onComplete, onError]);

  useEffect(() => {
    let timer: NodeJS.Timeout;

    const poll = async () => {
      const shouldContinue = await pollStatus();
      if (shouldContinue) {
        timer = setTimeout(poll, 2000);
      }
    };

    poll();
    return () => clearTimeout(timer);
  }, [pollStatus]);

  const progress = status?.progress ?? 0;
  const completedSteps = status?.steps_completed ?? [];

  return (
    <div className="max-w-2xl mx-auto mt-12 px-4">
      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Scanning Repository</h2>
          <span className="text-sm text-gray-400">{progress}%</span>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-700 rounded-full h-2 mb-6 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Steps */}
        <div className="space-y-3">
          {ALL_STEPS.map((step) => {
            const isCompleted = completedSteps.includes(step);
            const isCurrent =
              !isCompleted &&
              status?.current_step === STEP_LABELS[step];
            return (
              <div key={step} className="flex items-center gap-3">
                <div className="w-6 h-6 flex items-center justify-center shrink-0">
                  {isCompleted ? (
                    <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : isCurrent ? (
                    <div className="w-4 h-4 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border-2 border-gray-600" />
                  )}
                </div>
                <span
                  className={`text-sm ${
                    isCompleted
                      ? "text-gray-300"
                      : isCurrent
                      ? "text-cyan-400 font-medium"
                      : "text-gray-500"
                  }`}
                >
                  {STEP_LABELS[step]}
                </span>
                {isCurrent && status?.current_step && (
                  <span className="text-xs text-gray-500 ml-auto">
                    {status.current_step}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {status?.status === "failed" && status.error && (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
            <p className="text-sm text-red-400">{status.error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
