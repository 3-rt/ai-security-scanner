"use client";

import type { ScanSummary } from "@/lib/api";

const STAT_CARDS = [
  { key: "critical" as const, label: "Critical", color: "from-red-500 to-red-600", textColor: "text-red-400" },
  { key: "high" as const, label: "High", color: "from-orange-500 to-orange-600", textColor: "text-orange-400" },
  { key: "medium" as const, label: "Medium", color: "from-yellow-500 to-yellow-600", textColor: "text-yellow-400" },
  { key: "low" as const, label: "Low", color: "from-blue-500 to-blue-600", textColor: "text-blue-400" },
];

export default function SummaryStats({ summary }: { summary: ScanSummary }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-5">
        <p className="text-sm text-gray-400">Total Issues</p>
        <p className="text-3xl font-bold mt-1">{summary.total}</p>
      </div>
      {STAT_CARDS.map(({ key, label, color, textColor }) => (
        <div key={key} className="bg-gray-800/50 border border-gray-700 rounded-xl p-5 relative overflow-hidden">
          <div className={`absolute top-0 left-0 w-1 h-full bg-gradient-to-b ${color}`} />
          <p className="text-sm text-gray-400">{label}</p>
          <p className={`text-3xl font-bold mt-1 ${textColor}`}>{summary[key]}</p>
        </div>
      ))}
    </div>
  );
}
