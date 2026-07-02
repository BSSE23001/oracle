import type { AgentLane, ResearchPhase } from "@/lib/useResearchStream";
import { SubtaskTypeTag } from "./StatusBadge";

const STAGES: { key: ResearchPhase[]; label: string; icon: string }[] = [
  { key: ["connecting", "planning"], label: "Planning", icon: "🧠" },
  { key: ["awaiting_review"],        label: "Review",   icon: "👁" },
  { key: ["dispatching"],            label: "Research", icon: "🔬" },
  { key: ["synthesizing"],           label: "Synthesis",icon: "✍️" },
  { key: ["fact_checking"],          label: "Verify",   icon: "✅" },
  { key: ["formatting_citations", "completed"], label: "Cite", icon: "📚" },
];

function stageIndex(phase: ResearchPhase): number {
  if (phase === "failed") return -1;
  const idx = STAGES.findIndex((s) => s.key.includes(phase));
  return idx === -1 ? 0 : idx;
}

function PipelineStepper({ phase }: { phase: ResearchPhase }) {
  const current = stageIndex(phase);
  const allDone = phase === "completed";
  return (
    <div className="flex items-center gap-0">
      {STAGES.map((stage, i) => {
        const done   = i < current || allDone;
        const active = i === current && !allDone && phase !== "failed";
        return (
          <div key={stage.label} className="flex items-center">
            <div className="flex flex-col items-center gap-0.5">
              <div
                className={`flex h-7 w-7 items-center justify-center rounded-full text-sm transition-all duration-500 ${
                  done
                    ? "bg-emerald-500 shadow-md"
                    : active
                    ? "bg-amber-500 shadow-md animate-pulse-ring"
                    : "bg-gray-200"
                }`}
              >
                {done ? (
                  <span className="text-white text-xs">✓</span>
                ) : (
                  <span className={`text-xs ${active ? "text-white" : "text-gray-400"}`}>
                    {stage.icon}
                  </span>
                )}
              </div>
              <span
                className={`font-mono text-[9px] uppercase tracking-wider ${
                  done ? "text-emerald-600" : active ? "text-amber-600 font-bold" : "text-gray-400"
                }`}
              >
                {stage.label}
              </span>
            </div>
            {i < STAGES.length - 1 && (
              <div className={`mx-1 h-0.5 w-6 rounded-full transition-all duration-500 ${done ? "bg-emerald-300" : "bg-gray-200"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function LaneCard({ lane }: { lane: AgentLane }) {
  const running = lane.status === "running";
  const done    = lane.status === "done";
  const errored = lane.status === "error";

  return (
    <div
      className={`relative animate-line-in overflow-hidden rounded-2xl border bg-white p-5 shadow-sm transition-all duration-300 hover:shadow-md ${
        running
          ? "border-amber-300 shadow-amber-100"
          : done
          ? "border-emerald-200 shadow-emerald-50"
          : errored
          ? "border-crimson-200 shadow-crimson-50"
          : "border-gray-200"
      }`}
    >
      {/* Running shimmer bar */}
      {running && (
        <div className="absolute bottom-0 left-0 right-0 h-1 overflow-hidden rounded-b-2xl bg-amber-100">
          <div className="h-full w-1/2 animate-signal-sweep rounded-full bg-amber-400" />
        </div>
      )}

      {/* Status dot */}
      <div className="mb-3 flex items-center justify-between">
        <SubtaskTypeTag type={lane.subtaskType} />
        <span className="relative flex h-2.5 w-2.5">
          {running && (
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
          )}
          <span
            className={`relative inline-flex h-2.5 w-2.5 rounded-full ${
              running ? "bg-amber-400" : done ? "bg-emerald-500" : "bg-crimson-500"
            }`}
          />
        </span>
      </div>

      <p className="text-sm font-medium text-gray-700 leading-snug">{lane.description}</p>

      {running && (
        <p className="mt-3 font-mono text-[11px] text-gray-400 animate-pulse">
          Researching…
        </p>
      )}

      {lane.result && (
        <div className="mt-4 space-y-2 border-t border-gray-100 pt-3">
          <p className="text-sm text-gray-600 leading-relaxed">{lane.result.summary}</p>
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] text-gray-400">
              {lane.result.sources.length} source{lane.result.sources.length !== 1 ? "s" : ""}
            </span>
            <span
              className={`flex items-center gap-1 rounded-full px-2.5 py-0.5 font-mono text-[11px] font-bold ${
                errored
                  ? "bg-crimson-50 text-crimson-600"
                  : "bg-emerald-50 text-emerald-700"
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${errored ? "bg-crimson-500" : "bg-emerald-500"}`} />
              {Math.round(lane.result.confidence * 100)}% confidence
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export function AgentWireBoard({ phase, lanes }: { phase: ResearchPhase; lanes: AgentLane[] }) {
  return (
    <div className="overflow-hidden rounded-3xl border border-gray-200 bg-gradient-to-br from-gray-50 to-white shadow-lg">
      {/* Header */}
      <div className="border-b border-gray-100 bg-white/60 px-6 py-4 backdrop-blur-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-cobalt-500 to-cobalt-700 text-sm text-white shadow-sm">
              ⚡
            </span>
            <div>
              <h2 className="font-mono text-xs font-bold tracking-[0.15em] text-gray-800 uppercase">
                Agent Wire Board
              </h2>
              <p className="font-mono text-[10px] text-gray-400">
                {lanes.filter((l) => l.status === "done").length}/{lanes.length} specialists complete
              </p>
            </div>
          </div>
          <PipelineStepper phase={phase} />
        </div>
      </div>

      {/* Lane grid */}
      <div className="p-6">
        {lanes.length === 0 ? (
          <div className="flex flex-col items-center py-10 text-center">
            <div className="mb-3 h-12 w-12 animate-spin-slow rounded-full border-2 border-gray-200 border-t-cobalt-400" />
            <p className="font-mono text-xs text-gray-400">Awaiting specialist dispatch…</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {lanes.map((lane) => (
              <LaneCard key={lane.subtaskId} lane={lane} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
