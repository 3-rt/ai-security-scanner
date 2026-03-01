import ScanForm from "@/components/ScanForm";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center px-4 py-24">
      <div className="text-center mb-12 max-w-3xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm mb-6">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          Powered by CodeQL + Claude AI
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-balance">
          AI-Enhanced Security
          <br />
          <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            Vulnerability Scanner
          </span>
        </h1>
        <p className="mt-6 text-lg text-gray-400 max-w-2xl mx-auto text-balance">
          Paste a GitHub repository URL to run CodeQL static analysis. Get AI-generated
          explanations, attack scenarios, and fix suggestions for every vulnerability found.
        </p>
      </div>

      <ScanForm />

      <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-3xl w-full">
        {[
          {
            title: "Static Analysis",
            desc: "CodeQL scans source code for security vulnerabilities using semantic analysis and dataflow tracking.",
          },
          {
            title: "AI Enhancement",
            desc: "Claude AI explains each finding in plain English with realistic attack scenarios and business impact.",
          },
          {
            title: "Fix Suggestions",
            desc: "Get secure code fixes with side-by-side diffs showing exactly how to remediate each vulnerability.",
          },
        ].map((card) => (
          <div
            key={card.title}
            className="bg-gray-800/30 border border-gray-800 rounded-xl p-5"
          >
            <h3 className="font-medium text-gray-200 mb-2">{card.title}</h3>
            <p className="text-sm text-gray-500 leading-relaxed">{card.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
