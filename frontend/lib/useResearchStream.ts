"use client";

import { useEffect, useReducer, useRef } from "react";
import { streamUrl } from "./api";
import type {
  AgentEventType,
  FactCheckVerdict,
  NodeUpdatePayload,
  ParsedAgentEvent,
  PlanReviewRequiredPayload,
  ResearchPlan,
  ResearchReport,
  SubtaskResult,
  SubtaskType,
} from "./types";

export interface LogEntry {
  type: AgentEventType;
  node: string | null;
  sequence: number;
  ts: number;
  summary: string;
}

export type LaneStatus = "running" | "done" | "error";

export interface AgentLane {
  subtaskId: string;
  subtaskType: SubtaskType;
  description: string;
  status: LaneStatus;
  result?: SubtaskResult;
}

export type ResearchPhase =
  | "connecting"
  | "planning"
  | "awaiting_review"
  | "dispatching"
  | "synthesizing"
  | "fact_checking"
  | "formatting_citations"
  | "completed"
  | "failed";

export interface ResearchStreamState {
  phase: ResearchPhase;
  query: string | null;
  plan: ResearchPlan | null;
  planRevisionFeedback: string | null;
  lanes: AgentLane[];
  factCheckVerdicts: FactCheckVerdict[];
  report: ResearchReport | null;
  errorMessage: string | null;
  lastSequence: number;
  /** Ordered list of every event received, for the Activity Log sidebar. */
  log: LogEntry[];
}

const initialState: ResearchStreamState = {
  phase: "connecting",
  query: null,
  plan: null,
  planRevisionFeedback: null,
  lanes: [],
  factCheckVerdicts: [],
  report: null,
  errorMessage: null,
  lastSequence: 0,
  log: [],
};

const EVENT_TYPES: AgentEventType[] = [
  "session_started",
  "node_update",
  "plan_review_required",
  "plan_decision_received",
  "session_completed",
  "session_failed",
];

/** Build a human-readable summary string for a given event. */
function buildSummary(event: ParsedAgentEvent): string {
  switch (event.type) {
    case "session_started": {
      const d = event.data as { query: string };
      return `Session started — "${d.query.slice(0, 60)}${d.query.length > 60 ? "…" : ""}"`;
    }
    case "plan_review_required":
      return "Research plan ready — awaiting your review";
    case "plan_decision_received": {
      const d = event.data as { approved: boolean; feedback?: string };
      return d.approved
        ? "Plan approved — dispatching specialist agents"
        : `Plan revision requested${d.feedback ? `: ${d.feedback.slice(0, 60)}` : ""}`;
    }
    case "node_update": {
      const d = event.data as NodeUpdatePayload;
      const node = event.node ?? "agent";
      if (d.subtask_results) {
        const done = d.subtask_results.filter((r) => !r.error).length;
        const erred = d.subtask_results.filter((r) => !!r.error).length;
        return `${node}: ${done} subtask${done !== 1 ? "s" : ""} done${erred ? `, ${erred} error${erred !== 1 ? "s" : ""}` : ""}`;
      }
      if (d.draft_sections) {
        return `${node}: draft sections produced (${d.draft_sections.length})`;
      }
      if (d.fact_check_verdicts) {
        return `${node}: ${d.fact_check_verdicts.length} fact-check verdict${d.fact_check_verdicts.length !== 1 ? "s" : ""}`;
      }
      if (d.report) {
        return `${node}: report formatted with ${d.report.citations.length} citation${d.report.citations.length !== 1 ? "s" : ""}`;
      }
      if (d.plan) {
        return `${node}: research plan created (${d.plan.subtasks.length} subtasks)`;
      }
      return `${node}: update received`;
    }
    case "session_completed":
      return "✓ Research completed — report ready";
    case "session_failed": {
      const d = event.data as { error: string };
      return `✕ Session failed: ${d.error?.slice(0, 80) ?? "unknown error"}`;
    }
    default:
      return event.type;
  }
}

function reducer(
  state: ResearchStreamState,
  event: ParsedAgentEvent,
): ResearchStreamState {
  // EventSource replays full history on every reconnect (it sends the last
  // seen `id:` back as `Last-Event-ID`, but our backend always replays from
  // the start regardless) — sequence numbers are strictly increasing per
  // session, so this is a correct and sufficient de-dupe.
  if (event.sequence !== 0 && event.sequence <= state.lastSequence) {
    return state;
  }
  const base: ResearchStreamState = {
    ...state,
    lastSequence: Math.max(state.lastSequence, event.sequence),
  };

  // Append the event to the activity log
  const newLogEntry: LogEntry = {
    type: event.type,
    node: event.node,
    sequence: event.sequence,
    ts: Date.now(),
    summary: buildSummary(event),
  };
  const log = [...state.log, newLogEntry];

  switch (event.type) {
    case "session_started": {
      const data = event.data as { query: string };
      return { ...base, log, phase: "planning", query: data.query };
    }

    case "plan_review_required": {
      const data = event.data as PlanReviewRequiredPayload;
      return { ...base, log, phase: "awaiting_review", plan: data.plan };
    }

    case "plan_decision_received": {
      const data = event.data as { approved: boolean; feedback?: string };
      if (data.approved) {
        const lanes: AgentLane[] = (state.plan?.subtasks ?? []).map(
          (subtask) => ({
            subtaskId: subtask.id,
            subtaskType: subtask.type,
            description: subtask.description,
            status: "running",
          }),
        );
        return {
          ...base,
          log,
          phase: "dispatching",
          lanes,
          planRevisionFeedback: null,
        };
      }
      return {
        ...base,
        log,
        phase: "planning",
        planRevisionFeedback: data.feedback ?? null,
      };
    }

    // Deliberately duck-typed on the payload shape rather than `event.node`
    // each node in the graph returns a structurally distinct update, so
    // this avoids hardcoding all four specialist node names here.
    case "node_update": {
      const data = event.data as NodeUpdatePayload;

      if (data.subtask_results) {
        let lanes = state.lanes;
        for (const result of data.subtask_results) {
          lanes = lanes.map((lane) =>
            lane.subtaskId === result.subtask_id
              ? { ...lane, status: result.error ? "error" : "done", result }
              : lane,
          );
        }
        return { ...base, log, phase: "dispatching", lanes };
      }
      if (data.draft_sections) {
        return { ...base, log, phase: "synthesizing" };
      }
      if (data.fact_check_verdicts) {
        return {
          ...base,
          log,
          phase: "fact_checking",
          factCheckVerdicts: data.fact_check_verdicts,
        };
      }
      if (data.report) {
        return { ...base, log, phase: "formatting_citations", report: data.report };
      }
      return { ...base, log };
    }

    case "session_completed": {
      return {
        ...base,
        log,
        phase: "completed",
        report: event.data as ResearchReport,
      };
    }

    case "session_failed": {
      const data = event.data as { error: string };
      return { ...base, log, phase: "failed", errorMessage: data.error };
    }

    default:
      return { ...base, log };
  }
}

export function useResearchStream(sessionId: string): ResearchStreamState {
  const [state, dispatch] = useReducer(reducer, initialState);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const source = new EventSource(streamUrl(sessionId));
    sourceRef.current = source;

    const listeners = EVENT_TYPES.map((type) => {
      const handler = (raw: MessageEvent) => {
        try {
          const envelope = JSON.parse(raw.data) as {
            node: string | null;
            data: unknown;
          };
          dispatch({
            type,
            node: envelope.node,
            sequence: Number(raw.lastEventId) || 0,
            data: envelope.data as ParsedAgentEvent["data"],
          });
        } catch (err) {
          console.error("Failed to parse SSE event", type, err);
        }
      };
      source.addEventListener(type, handler);
      return { type, handler };
    });

    return () => {
      for (const { type, handler } of listeners) {
        source.removeEventListener(type, handler);
      }
      source.close();
    };
  }, [sessionId]);

  return state;
}
