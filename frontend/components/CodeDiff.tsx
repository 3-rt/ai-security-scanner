"use client";

import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface CodeDiffProps {
  vulnerableCode: string;
  fixedCode: string;
  language?: string;
}

export default function CodeDiff({ vulnerableCode, fixedCode, language = "python" }: CodeDiffProps) {
  const [view, setView] = useState<"side-by-side" | "vulnerable" | "fixed">("side-by-side");
  const [copied, setCopied] = useState(false);

  const langMap: Record<string, string> = {
    python: "python",
    javascript: "javascript",
    java: "java",
    csharp: "csharp",
    go: "go",
    ruby: "ruby",
    cpp: "cpp",
  };

  const syntaxLang = langMap[language] || "text";

  const copyFixed = () => {
    navigator.clipboard.writeText(fixedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const codeStyle = {
    ...oneDark,
    'pre[class*="language-"]': {
      ...oneDark['pre[class*="language-"]'],
      background: "transparent",
      margin: 0,
      padding: "1rem",
      fontSize: "0.8125rem",
    },
    'code[class*="language-"]': {
      ...oneDark['code[class*="language-"]'],
      background: "transparent",
    },
  };

  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-3">
        <div className="flex bg-gray-800 rounded-lg p-0.5">
          {(["side-by-side", "vulnerable", "fixed"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                view === v ? "bg-gray-700 text-white" : "text-gray-400 hover:text-gray-200"
              }`}
            >
              {v === "side-by-side" ? "Side by Side" : v === "vulnerable" ? "Vulnerable" : "Fixed"}
            </button>
          ))}
        </div>
        <button
          onClick={copyFixed}
          className="ml-auto px-3 py-1.5 text-xs font-medium bg-emerald-600/20 text-emerald-400 rounded-lg hover:bg-emerald-600/30 transition-colors"
        >
          {copied ? "Copied!" : "Copy Fix"}
        </button>
      </div>

      {view === "side-by-side" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="rounded-lg overflow-hidden border border-red-500/20 bg-red-950/10">
            <div className="px-3 py-1.5 bg-red-500/10 text-red-400 text-xs font-medium border-b border-red-500/20">
              Vulnerable Code
            </div>
            <SyntaxHighlighter language={syntaxLang} style={codeStyle} showLineNumbers wrapLongLines>
              {vulnerableCode || "(not available)"}
            </SyntaxHighlighter>
          </div>
          <div className="rounded-lg overflow-hidden border border-emerald-500/20 bg-emerald-950/10">
            <div className="px-3 py-1.5 bg-emerald-500/10 text-emerald-400 text-xs font-medium border-b border-emerald-500/20">
              Fixed Code
            </div>
            <SyntaxHighlighter language={syntaxLang} style={codeStyle} showLineNumbers wrapLongLines>
              {fixedCode || "(not available)"}
            </SyntaxHighlighter>
          </div>
        </div>
      ) : (
        <div
          className={`rounded-lg overflow-hidden border ${
            view === "vulnerable" ? "border-red-500/20 bg-red-950/10" : "border-emerald-500/20 bg-emerald-950/10"
          }`}
        >
          <div
            className={`px-3 py-1.5 text-xs font-medium border-b ${
              view === "vulnerable"
                ? "bg-red-500/10 text-red-400 border-red-500/20"
                : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
            }`}
          >
            {view === "vulnerable" ? "Vulnerable Code" : "Fixed Code"}
          </div>
          <SyntaxHighlighter language={syntaxLang} style={codeStyle} showLineNumbers wrapLongLines>
            {(view === "vulnerable" ? vulnerableCode : fixedCode) || "(not available)"}
          </SyntaxHighlighter>
        </div>
      )}
    </div>
  );
}
