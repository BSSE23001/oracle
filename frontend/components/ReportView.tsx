import type { FactCheckVerdict, ResearchReport } from "@/lib/types";
import { ConfidenceGauge } from "@/components/ConfidenceGauge";
import { FeedbackForm } from "@/components/FeedbackForm";

const VERDICT_STYLES: Record<FactCheckVerdict["verdict"], string> = {
  supported: "border-teal-600 text-teal-400",
  contradicted: "border-rust-600 text-rust-400",
  uncertain: "border-ink-500 text-muted-500",
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
    <div className="mt-3 flex flex-wrap gap-2">
      {citationIds.map((id) => {
        const citation = byId.get(id);
        if (!citation) return null;
        const href = citation.doi ? `https://doi.org/${citation.doi}` : citation.url ?? undefined;
        const label = citation.title ?? id;
        const inner = (
          <>
            <span className="text-brass-400">[{id}]</span> {label}
          </>
        );
        return href ? (
          <a
            key={id}
            href={href}
            target="_blank"
            rel="noreferrer"
            className="rounded-sm border border-ink-600 px-2 py-1 font-mono text-[11px] text-muted-500 transition-colors hover:border-brass-500 hover:text-brass-300"
          >
            {inner}
          </a>
        ) : (
          <span key={id} className="rounded-sm border border-ink-600 px-2 py-1 font-mono text-[11px] text-muted-500">
            {inner}
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
      <div className="rounded-md border border-ink-500 bg-ink-700 p-8 shadow-panel">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="mb-2 font-mono text-xs tracking-[0.2em] text-brass-400 uppercase">Research report</p>
            <h1 className="font-display text-3xl text-parchment-100">{report.title}</h1>
            <p className="mt-3 max-w-2xl text-muted-500">{report.summary}</p>
          </div>
          <ConfidenceGauge score={report.confidence_score} />
        </div>
      </div>

      <div className="space-y-6">
        {report.sections.map((section) => (
          <div key={section.heading} className="rounded-md border border-ink-600 bg-ink-800 p-6">
            <h2 className="font-display text-xl text-parchment-100">{section.heading}</h2>
            <div className="mt-3 space-y-3 text-parchment-300">
              {section.content.split("\n\n").map((paragraph, i) => (
                <p key={i}>{paragraph}</p>
              ))}
            </div>
            <CitationChips citationIds={section.citation_ids} citations={report.citations} />
          </div>
        ))}
      </div>

      {factCheckVerdicts.length > 0 && (
        <div className="rounded-md border border-ink-600 bg-ink-800 p-6">
          <h2 className="mb-4 font-mono text-xs tracking-[0.2em] text-brass-400 uppercase">Fact-check appendix</h2>
          <ul className="space-y-3">
            {factCheckVerdicts.map((verdict, i) => (
              <li key={i} className={`rounded-sm border-l-2 ${VERDICT_STYLES[verdict.verdict]} bg-ink-700 p-4`}>
                <div className="flex items-center justify-between">
                  <p className="text-sm text-parchment-100">{verdict.claim}</p>
                  <span className={`ml-3 shrink-0 font-mono text-[11px] uppercase ${VERDICT_STYLES[verdict.verdict]}`}>
                    {verdict.verdict}
                  </span>
                </div>
                <p className="mt-2 text-xs text-muted-500">{verdict.explanation}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {report.citations.length > 0 && (
        <div className="rounded-md border border-ink-600 bg-ink-800 p-6">
          <h2 className="mb-4 font-mono text-xs tracking-[0.2em] text-brass-400 uppercase">Citations</h2>
          <ul className="space-y-2">
            {report.citations.map((c) => {
              const href = c.doi ? `https://doi.org/${c.doi}` : c.url ?? undefined;
              const authorStr = c.authors.length
                ? `${c.authors.slice(0, 3).join(", ")}${c.authors.length > 3 ? " et al." : ""} — `
                : "";
              return (
                <li key={c.id} className="font-mono text-xs text-muted-500">
                  <span className="text-brass-400">[{c.id}]</span> {authorStr}
                  {href ? (
                    <a
                      href={href}
                      target="_blank"
                      rel="noreferrer"
                      className="text-parchment-300 underline-offset-2 hover:underline"
                    >
                      {c.title ?? href}
                    </a>
                  ) : (
                    <span className="text-parchment-300">{c.title ?? "Untitled source"}</span>
                  )}
                  {c.year ? ` (${c.year})` : ""}
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
