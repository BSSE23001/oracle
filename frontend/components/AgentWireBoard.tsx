import type { AgentLane, ResearchPhase } from "@/lib/useResearchStream";
import { SubtaskTypeTag } from "./StatusBadge";

const STAGES: { key: ResearchPhase[]; label: string }[] = [
  { key: ["connecting", "planning"], label: "Supervisor" },
  { key: ["awaiting_review"], label: "Review" },
  { key: ["dispatching"], label: "Specialists" },
  { key: ["synthesizing"], label: "Synthesis" },
  { key: ["fact_checking"], label: "Fact-check" },
  { key: ["formatting_citations", "completed"], label: "Citations" },
];

function stageIndex(phase: ResearchPhase): number {
  if (phase === "failed") return -1;
  const idx = STAGES.findIndex((stage) => stage.key.includes(phase));
  return idx === -1 ? 0 : idx;
}

function PipelineStepper({ phase }: { phase: ResearchPhase }) {
  const current = stageIndex(phase);
  return (
    <div className="flex items-center gap-1 font-mono text-[11px] tracking-wider uppercase">
      {STAGES.map((stage, i) => {
        const done = i < current || phase === "completed";
        const active = i === current && phase !== "completed";
        return (
          <div key={stage.label} className="flex items-center gap-1">
            <span
              className={
                done
                  ? "text-teal-400"
                  : active
                    ? "text-brass-400"
                    : phase === "failed"
                      ? "text-rust-500/60"
                      : "text-muted-600"
              }
            >
              {stage.label}
            </span>
            {i < STAGES.length - 1 && <span className="px-1 text-ink-500">→</span>}
          </div>
        );
      })}
    </div>
  );
}

function LaneCard({ lane }: { lane: AgentLane }) {
  const dot =
    lane.status === "running" ? (
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brass-400 opacity-75" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-brass-400" />
      </span>
    ) : lane.status === "done" ? (
      <span className="h-2 w-2 rounded-full bg-teal-400" />
    ) : (
      <span className="h-2 w-2 rounded-full bg-rust-500" />
    );

  return (
    <div className="animate-line-in flex flex-col rounded-md border border-ink-600 bg-ink-700 p-4">
      <div className="mb-2 flex items-center justify-between">
        <SubtaskTypeTag type={lane.subtaskType} />
        {dot}
      </div>
      <p className="text-sm text-parchment-300">{lane.description}</p>

      {lane.status === "running" && (
        <p className="mt-3 font-mono text-[11px] text-muted-500">awaiting response…</p>
      )}

      {lane.result && (
        <div className="mt-3 border-t border-ink-600 pt-3">
          <p className="text-sm text-parchment-100">{lane.result.summary}</p>
          <div className="mt-2 flex items-center justify-between font-mono text-[11px] text-muted-500">
            <span>
              {lane.result.sources.length} source{lane.result.sources.length === 1 ? "" : "s"}
            </span>
            <span className={lane.status === "error" ? "text-rust-400" : "text-teal-400"}>
              confidence {Math.round(lane.result.confidence * 100)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export function AgentWireBoard({ phase, lanes }: { phase: ResearchPhase; lanes: AgentLane[] }) {
  return (
    <div className="rounded-md border border-ink-500 bg-ink-800 p-6 shadow-panel">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="font-mono text-xs tracking-[0.2em] text-brass-400 uppercase">Agent wire board</h2>
        <PipelineStepper phase={phase} />
      </div>

      {lanes.length === 0 ? (
        <p className="font-mono text-xs text-muted-600">no specialists dispatched yet</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {lanes.map((lane) => (
            <LaneCard key={lane.subtaskId} lane={lane} />
          ))}
        </div>
      )}
    </div>
  );
}
