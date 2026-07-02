import type { FactCheckVerdict, ResearchReport } from "@/lib/types";
import { ConfidenceGauge } from "@/components/ConfidenceGauge";
import { FeedbackForm } from "@/components/FeedbackForm";

const VERDICT_CONFIG: Record<
  FactCheckVerdict["verdict"],
  { border: string; bg: string; text: string; badge: string; badgeBg: string; icon: string }
> = {
  supported:    { border: "border-l-emerald-500", bg: "bg-emerald-50",  text: "text-emerald-800", badge: "text-emerald-700", badgeBg: "bg-emerald-100", icon: "✓" },
  contradicted: { border: "border-l-crimson-500",  bg: "bg-crimson-50",  text: "text-crimson-800", badge: "text-crimson-700", badgeBg: "bg-crimson-100", icon: "✕" },
  uncertain:    { border: "border-l-amber-500",    bg: "bg-amber-50",    text: "text-amber-800",   badge: "text-amber-700",  badgeBg: "bg-amber-100",   icon: "?" },
};

function CitationChips({
  citationIds,
  citations,
}: {
  citationIds: string[];
  citations: ResearchReport["citations"];
}) {
  if (citationIds.length === 0) return null;
  const byId = new Map(citations.map((c) => [c.id, c]));
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {citationIds.map((id) => {
        const citation = byId.get(id);
        if (!citation) return null;
        const href = citation.doi ? `https://doi.org/${citation.doi}` : citation.url ?? undefined;
        const label = citation.title ?? id;
        const chip = (
          <span className="inline-flex items-center gap-1.5">
            <span className="font-bold text-cobalt-600">[{id}]</span>
            <span className="truncate max-w-[200px]">{label}</span>
            {href && <span className="text-gray-400">↗</span>}
          </span>
        );
        return href ? (
          <a
            key={id}
            href={href}
            target="_blank"
            rel="noreferrer"
            className="inline-flex max-w-xs items-center truncate rounded-lg border border-cobalt-100 bg-cobalt-50 px-3 py-1 font-mono text-[11px] text-cobalt-700 transition-all hover:border-cobalt-300 hover:bg-cobalt-100 hover:shadow-sm"
          >
            {chip}
          </a>
        ) : (
          <span key={id} className="inline-flex max-w-xs items-center truncate rounded-lg border border-gray-200 bg-gray-50 px-3 py-1 font-mono text-[11px] text-gray-500">
            {chip}
          </span>
        );
      })}
    </div>
  );
}

export function ReportView({
  report,
  reportId,
  factCheckVerdicts,
}: {
  report: ResearchReport;
  reportId: string | null;
  factCheckVerdicts: FactCheckVerdict[];
}) {
  return (
    <div className="animate-line-in space-y-8">
      {/* ── Report header card ────────────────────────────────────────────── */}
      <div className="relative overflow-hidden rounded-3xl border border-emerald-200 bg-gradient-to-br from-emerald-50 via-white to-cobalt-50 p-8 shadow-xl">
        {/* Sparkle accents */}
        <span aria-hidden className="pointer-events-none absolute right-8 top-6 animate-sparkle text-amber-300 text-2xl">✦</span>
        <span aria-hidden className="pointer-events-none absolute right-16 top-14 animate-sparkle text-emerald-300 text-sm" style={{ animationDelay: "1.2s" }}>✦</span>

        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex-1">
            <p className="mb-2 flex items-center gap-2 font-mono text-xs font-bold tracking-[0.2em] text-emerald-600 uppercase">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Research Report
            </p>
            <h1 className="font-display text-3xl font-semibold text-gray-900 leading-tight sm:text-4xl">
              {report.title}
            </h1>
            <p className="mt-4 max-w-2xl text-base text-gray-500 leading-relaxed">{report.summary}</p>
          </div>
          <div className="shrink-0">
            <ConfidenceGauge score={report.confidence_score} />
          </div>
        </div>
      </div>

      {/* ── Report sections ───────────────────────────────────────────────── */}
      <div className="space-y-5">
        {report.sections.map((section, idx) => (
          <div
            key={section.heading}
            className="group rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition-all duration-200 hover:border-emerald-200 hover:shadow-md"
          >
            <div className="mb-4 flex items-center gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-400 to-emerald-600 font-mono text-xs font-bold text-white shadow-sm">
                {idx + 1}
              </span>
              <h2 className="font-display text-xl font-semibold text-gray-900">{section.heading}</h2>
            </div>
            <div className="space-y-3 text-gray-600 leading-relaxed">
              {section.content.split("\n\n").map((para, i) => (
                <p key={i}>{para}</p>
              ))}
            </div>
            <CitationChips citationIds={section.citation_ids} citations={report.citations} />
          </div>
        ))}
      </div>

      {/* ── Fact-check appendix ───────────────────────────────────────────── */}
      {factCheckVerdicts.length > 0 && (
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-cobalt-500 to-cobalt-700 text-sm text-white shadow-sm">✅</span>
            <h2 className="font-mono text-xs font-bold tracking-[0.2em] text-gray-700 uppercase">Fact-Check Appendix</h2>
          </div>
          <ul className="space-y-3">
            {factCheckVerdicts.map((verdict, i) => {
              const cfg = VERDICT_CONFIG[verdict.verdict];
              return (
                <li
                  key={i}
                  className={`rounded-xl border-l-4 p-4 ${cfg.border} ${cfg.bg}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className={`text-sm font-medium ${cfg.text}`}>{verdict.claim}</p>
                    <span className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2.5 py-0.5 font-mono text-[10px] font-bold uppercase ${cfg.badge} ${cfg.badgeBg}`}>
                      <span>{cfg.icon}</span>
                      {verdict.verdict}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-gray-500">{verdict.explanation}</p>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* ── Citations ────────────────────────────────────────────────────── */}
      {report.citations.length > 0 && (
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 text-sm text-white shadow-sm">📚</span>
            <h2 className="font-mono text-xs font-bold tracking-[0.2em] text-gray-700 uppercase">Citations</h2>
          </div>
          <ul className="space-y-2.5">
            {report.citations.map((c) => {
              const href = c.doi ? `https://doi.org/${c.doi}` : c.url ?? undefined;
              const authorStr = c.authors.length
                ? `${c.authors.slice(0, 3).join(", ")}${c.authors.length > 3 ? " et al." : ""} — `
                : "";
              return (
                <li key={c.id} className="flex items-baseline gap-2 font-mono text-xs">
                  <span className="shrink-0 rounded-md bg-cobalt-50 px-2 py-0.5 font-bold text-cobalt-600 border border-cobalt-100">[{c.id}]</span>
                  <span className="text-gray-500">{authorStr}</span>
                  {href ? (
                    <a href={href} target="_blank" rel="noreferrer" className="text-gray-700 underline-offset-2 hover:underline hover:text-emerald-700 transition-colors">
                      {c.title ?? href}
                    </a>
                  ) : (
                    <span className="text-gray-700">{c.title ?? "Untitled source"}</span>
                  )}
                  {c.year && <span className="text-gray-400">({c.year})</span>}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {reportId && <FeedbackForm reportId={reportId} />}
    </div>
  );
}
