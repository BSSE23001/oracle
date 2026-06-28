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
};

const EVENT_TYPES: AgentEventType[] = [
  "session_started",
  "node_update",
  "plan_review_required",
  "plan_decision_received",
  "session_completed",
  "session_failed",
];

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

  switch (event.type) {
    case "session_started": {
      const data = event.data as { query: string };
      return { ...base, phase: "planning", query: data.query };
    }

    case "plan_review_required": {
      const data = event.data as PlanReviewRequiredPayload;
      return { ...base, phase: "awaiting_review", plan: data.plan };
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
          phase: "dispatching",
          lanes,
          planRevisionFeedback: null,
        };
      }
      return {
        ...base,
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
        return { ...base, phase: "dispatching", lanes };
      }
      if (data.draft_sections) {
        return { ...base, phase: "synthesizing" };
      }
      if (data.fact_check_verdicts) {
        return {
          ...base,
          phase: "fact_checking",
          factCheckVerdicts: data.fact_check_verdicts,
        };
      }
      if (data.report) {
        return { ...base, phase: "formatting_citations", report: data.report };
      }
      return base;
    }

    case "session_completed": {
      return {
        ...base,
        phase: "completed",
        report: event.data as ResearchReport,
      };
    }

    case "session_failed": {
      const data = event.data as { error: string };
      return { ...base, phase: "failed", errorMessage: data.error };
    }

    default:
      return base;
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
