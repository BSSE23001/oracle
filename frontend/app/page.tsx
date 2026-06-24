import Link from "next/link";
import { QueryForm } from "@/components/QueryForm";

export default function HomePage() {
  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6">
      <div className="absolute inset-x-0 top-0 h-px overflow-hidden bg-ink-600">
        <div className="h-px w-1/3 animate-signal-sweep bg-brass-500/60" />
      </div>

      <header className="absolute top-0 left-0 flex w-full items-center justify-between px-6 py-5 font-mono text-xs tracking-[0.2em] text-muted-500 uppercase">
        <span>ORACLE // RESEARCH DESK</span>
        <div className="flex items-center gap-6">
          <Link href="/history" className="hover:text-brass-300 transition-colors">History</Link>
          <span className="flex items-center gap-2 text-teal-400">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal-400" />
            ONLINE
          </span>
        </div>
      </header>

      <div className="flex max-w-3xl flex-col items-center text-center">
        <p className="mb-4 font-mono text-xs tracking-[0.3em] text-brass-400 uppercase">
          Multi-agent research intelligence
        </p>
        <h1 className="font-display text-4xl leading-tight text-parchment-100 italic sm:text-5xl">
          Ask a question.
          <br className="hidden sm:block" /> Watch it get researched.
        </h1>
        <p className="mt-4 max-w-lg text-muted-500">
          A supervisor agent plans the work, dispatches specialists to search, read, and compute in
          parallel, then writes a cited report — fact-checked against its own claims before you see it.
        </p>
      </div>

      <div className="mt-10">
        <QueryForm />
      </div>
    </main>
  );
}
