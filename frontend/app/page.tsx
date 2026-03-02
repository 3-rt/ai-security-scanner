import ScanForm from "@/components/ScanForm";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center px-4 py-24">
      <div className="text-center mb-12 max-w-3xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gray-100 border border-gray-200 text-gray-600 text-sm mb-6">
          Powered by Semgrep + Claude AI
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-gray-900 text-balance">
          AI-Enhanced Security
          <br />
          Vulnerability Scanner
        </h1>
        <p className="mt-6 text-lg text-gray-500 max-w-2xl mx-auto text-balance">
          Paste a GitHub repository URL to run Semgrep static analysis. Get AI-generated
          explanations, attack scenarios, and fix suggestions for every vulnerability found.
        </p>
      </div>

      <ScanForm />

      <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-3xl w-full">
        {[
          {
            title: "Static Analysis",
            desc: "Semgrep scans source code for security vulnerabilities using pattern matching and dataflow analysis.",
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
            className="bg-white border border-gray-200 rounded-xl p-5"
          >
            <h3 className="font-medium text-gray-900 mb-2">{card.title}</h3>
            <p className="text-sm text-gray-500 leading-relaxed">{card.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
