import Link from "next/link";

const PIPELINE = [
  {
    step: 1, icon: "🧠", title: "Supervisor Planning",
    color: "from-violet-500 to-purple-600", text: "text-violet-700", bg: "bg-violet-50", border: "border-violet-200",
    desc: "Decomposes your query into a structured research plan with parallel subtasks, each assigned to the right specialist agent.",
  },
  {
    step: 2, icon: "👁", title: "Human Review",
    color: "from-amber-400 to-amber-600", text: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200",
    desc: "You review and optionally revise the plan before agents are dispatched — giving you full control over what gets researched.",
  },
  {
    step: 3, icon: "🌐", title: "Parallel Web Search",
    color: "from-cobalt-500 to-cobalt-700", text: "text-cobalt-700", bg: "bg-cobalt-50", border: "border-cobalt-200",
    desc: "Web search agents query Tavily for each subtask simultaneously, returning scored and extracted page content.",
  },
  {
    step: 4, icon: "📄", title: "PDF Reader Agent",
    color: "from-amber-500 to-orange-600", text: "text-orange-700", bg: "bg-orange-50", border: "border-orange-200",
    desc: "Reads, chunks, and semantically embeds full PDF documents using ChromaDB for vector-similarity retrieval.",
  },
  {
    step: 5, icon: "✍️", title: "Synthesis",
    color: "from-emerald-500 to-emerald-700", text: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200",
    desc: "A synthesis LLM merges all parallel findings into a coherent, structured report with sections and inline source references.",
  },
  {
    step: 6, icon: "✅", title: "Fact-Check Pass",
    color: "from-crimson-500 to-crimson-700", text: "text-crimson-700", bg: "bg-crimson-50", border: "border-crimson-200",
    desc: "Extracts up to 5 key claims from the draft and verifies each against fresh web evidence in parallel, producing supported / contradicted / uncertain verdicts.",
  },
  {
    step: 7, icon: "📚", title: "Citation Formatter",
    color: "from-gray-600 to-gray-800", text: "text-gray-700", bg: "bg-gray-50", border: "border-gray-200",
    desc: "Deduplicates all sources, resolves academic DOIs via CrossRef in parallel, and assembles a final, properly-cited report.",
  },
];

const TECH = [
  { name: "LangGraph",     desc: "Stateful multi-agent orchestration with human-in-the-loop interrupts", color: "bg-violet-100 text-violet-800 border-violet-200" },
  { name: "LangChain",     desc: "LLM abstraction layer, structured output, prompt templates",           color: "bg-cobalt-100 text-cobalt-800 border-cobalt-200" },
  { name: "OpenRouter",    desc: "Multi-model LLM gateway with automatic fallback across free models",   color: "bg-amber-100 text-amber-800 border-amber-200" },
  { name: "Tavily",        desc: "AI-native web search API returning clean, ranked content",             color: "bg-emerald-100 text-emerald-800 border-emerald-200" },
  { name: "ChromaDB",      desc: "Local vector database for semantic document chunking and retrieval",  color: "bg-pink-100 text-pink-800 border-pink-200" },
  { name: "PostgreSQL",    desc: "Persistent graph checkpoint store and session / report database",     color: "bg-blue-100 text-blue-800 border-blue-200" },
  { name: "Celery + Redis","desc": "Distributed task queue — runs long research tasks as background jobs", color: "bg-red-100 text-red-800 border-red-200" },
  { name: "FastAPI",       desc: "Async backend API with Server-Sent Events for real-time streaming",   color: "bg-teal-100 text-teal-800 border-teal-200" },
  { name: "Next.js 16",    desc: "React 19 frontend with App Router, streaming and Tailwind CSS v4",   color: "bg-gray-100 text-gray-800 border-gray-200" },
];

const STEPS = [
  { n: "01", title: "Type your question", desc: "Enter any research question in the box on the home page. The more specific, the better the plan." },
  { n: "02", title: "Review the plan",    desc: "The supervisor proposes a set of parallel subtasks. Approve as-is or request changes with a note." },
  { n: "03", title: "Watch agents work",  desc: "Specialist agents research your subtasks in parallel. The wire board shows their live progress." },
  { n: "04", title: "Read the report",    desc: "A synthesized, fact-checked, fully cited report appears when all agents complete their work." },
  { n: "05", title: "Rate & iterate",     desc: "Leave a star rating. Start a new query. History tab shows all your previous research sessions." },
];

export default function AboutPage() {
  return (
    <main className="min-h-[calc(100vh-4rem)] bg-white">
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-gray-100 bg-gradient-to-br from-gray-50 via-white to-emerald-50 px-6 py-20 text-center">
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div className="absolute left-1/4 top-0 h-64 w-64 -translate-x-1/2 rounded-full bg-emerald-200/40 blur-3xl" />
          <div className="absolute right-1/4 bottom-0 h-64 w-64 translate-x-1/2 rounded-full bg-cobalt-200/40 blur-3xl" />
        </div>
        <div className="relative mx-auto max-w-3xl">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/80 px-4 py-1.5 shadow-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span className="font-mono text-xs font-semibold tracking-widest text-emerald-700 uppercase">How ORACLE works</span>
          </div>
          <h1 className="mb-4 font-display text-5xl font-semibold text-gray-900 italic leading-tight">
            Research, <span className="gradient-text-green">reimagined</span>
          </h1>
          <p className="text-lg text-gray-500 leading-relaxed">
            ORACLE is an autonomous multi-agent research assistant. It doesn&apos;t just search — it{" "}
            <strong className="font-semibold text-gray-700">plans</strong>,{" "}
            <strong className="font-semibold text-gray-700">delegates</strong>,{" "}
            <strong className="font-semibold text-gray-700">synthesizes</strong>, and{" "}
            <strong className="font-semibold text-gray-700">fact-checks</strong> before producing a cited report.
          </p>
        </div>
      </section>

      {/* Pipeline */}
      <section className="mx-auto max-w-5xl px-6 py-20">
        <h2 className="mb-2 text-center font-mono text-xs font-bold tracking-[0.25em] text-gray-400 uppercase">The pipeline</h2>
        <p className="mb-12 text-center font-display text-3xl font-semibold text-gray-900 italic">Seven stages from question to report</p>

        <div className="relative">
          {/* Connector line */}
          <div aria-hidden className="absolute left-6 top-8 bottom-8 w-px bg-gradient-to-b from-violet-300 via-emerald-300 to-gray-300 sm:left-1/2 sm:-translate-x-1/2" />

          <div className="space-y-6">
            {PIPELINE.map((item, i) => (
              <div
                key={item.step}
                className={`relative flex gap-5 ${i % 2 === 0 ? "sm:flex-row" : "sm:flex-row-reverse sm:text-right"}`}
              >
                {/* Step card */}
                <div className={`flex-1 rounded-2xl border ${item.border} ${item.bg} p-5 shadow-sm transition-all hover:shadow-md`}>
                  <div className={`mb-2 flex items-center gap-2 ${i % 2 !== 0 ? "sm:justify-end" : ""}`}>
                    <span className={`flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br ${item.color} text-white shadow-sm`}>
                      {item.icon}
                    </span>
                    <h3 className={`font-mono text-xs font-bold tracking-wider uppercase ${item.text}`}>{item.title}</h3>
                  </div>
                  <p className="text-sm text-gray-600 leading-relaxed">{item.desc}</p>
                </div>

                {/* Step number bubble */}
                <div className="relative flex shrink-0 items-start justify-center sm:w-12">
                  <div className={`relative z-10 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br ${item.color} font-mono text-xs font-bold text-white shadow-lg`}>
                    {item.step}
                  </div>
                </div>

                {/* Spacer on alternating side */}
                <div className="hidden flex-1 sm:block" />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How to use */}
      <section className="border-y border-gray-100 bg-gradient-to-br from-cobalt-50 to-white px-6 py-20">
        <div className="mx-auto max-w-4xl">
          <h2 className="mb-2 text-center font-mono text-xs font-bold tracking-[0.25em] text-gray-400 uppercase">Getting started</h2>
          <p className="mb-12 text-center font-display text-3xl font-semibold text-gray-900 italic">How to use ORACLE</p>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {STEPS.map((step) => (
              <div key={step.n} className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:border-emerald-200 hover:shadow-md">
                <div className="mb-3 flex items-center gap-3">
                  <span className="font-mono text-2xl font-black text-emerald-200">{step.n}</span>
                  <h3 className="font-mono text-xs font-bold tracking-wider text-gray-700 uppercase">{step.title}</h3>
                </div>
                <p className="text-sm text-gray-500 leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech stack */}
      <section className="mx-auto max-w-5xl px-6 py-20">
        <h2 className="mb-2 text-center font-mono text-xs font-bold tracking-[0.25em] text-gray-400 uppercase">Under the hood</h2>
        <p className="mb-12 text-center font-display text-3xl font-semibold text-gray-900 italic">Technology stack</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {TECH.map((t) => (
            <div key={t.name} className={`rounded-xl border px-4 py-3 ${t.color}`}>
              <p className="font-mono text-xs font-bold tracking-wider uppercase">{t.name}</p>
              <p className="mt-1 text-xs opacity-80 leading-relaxed">{t.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-gray-100 bg-gradient-to-br from-emerald-500 to-emerald-700 px-6 py-16 text-center text-white">
        <div aria-hidden className="pointer-events-none absolute inset-0 opacity-10"
          style={{ backgroundImage: "radial-gradient(circle, white 1px, transparent 1px)", backgroundSize: "24px 24px" }} />
        <h2 className="mb-3 font-display text-3xl font-semibold italic">Ready to research?</h2>
        <p className="mb-8 text-emerald-100">Ask your first question and watch ORACLE go to work.</p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-2xl bg-white px-8 py-3.5 font-mono text-sm font-bold tracking-wider text-emerald-700 shadow-xl transition-all hover:scale-105 hover:shadow-2xl active:scale-95"
        >
          Start Researching ▸
        </Link>
      </section>
    </main>
  );
}
