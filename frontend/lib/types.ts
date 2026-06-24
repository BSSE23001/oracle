// Mirrors backend/app/agents/schemas.py and backend/app/api/schemas.py.
// Kept in one file since the frontend has no codegen step against the
// FastAPI OpenAPI schema (yet), if you add one later (e.g. `openapi-typescript`
// pointed at /openapi.json), this file is what it would replace.

export type SubtaskType =
  | "web_search"
  | "pdf_reader"
  | "code_exec"
  | "fact_check";

export interface Subtask {
  id: string;
  type: SubtaskType;
  description: string;
  input_data: string;
}

export interface ResearchPlan {
  objective: string;
  subtasks: Subtask[];
}

export interface SourceRef {
  url?: string | null;
  title?: string | null;
  doi?: string | null;
}

export interface SubtaskResult {
  subtask_id: string;
  subtask_type: SubtaskType;
  summary: string;
  sources: SourceRef[];
  confidence: number;
  raw_excerpt?: string;
  error?: string | null;
}

export type FactCheckVerdictLabel = "supported" | "contradicted" | "uncertain";

export interface FactCheckVerdict {
  claim: string;
  verdict: FactCheckVerdictLabel;
  explanation: string;
  sources: SourceRef[];
}

export interface Citation {
  id: string;
  title?: string | null;
  authors: string[];
  year?: number | null;
  venue?: string | null;
  url?: string | null;
  doi?: string | null;
}

export interface ReportSection {
  heading: string;
  content: string;
  citation_ids: string[];
}

export interface ResearchReport {
  title: string;
  summary: string;
  sections: ReportSection[];
  citations: Citation[];
  confidence_score: number;
}

export type SessionStatus =
  | "pending"
  | "planning"
  | "awaiting_review"
  | "running"
  | "completed"
  | "failed";

export interface ReportSummary {
  id: string;
  session_id: string;
  title: string;
  summary: string;
  sections: ReportSection[];
  citations: Citation[];
  confidence_score: number;
  created_at: string;
}

export interface ResearchSessionResponse {
  id: string;
  query: string;
  status: SessionStatus;
  plan: ResearchPlan | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  report: ReportSummary | null;
}

// ── SSE event envelope ───────────────────────────────────────────────────
// Matches the `{event, id, data}` shape app/api/routes_research.py's
// `_sse_message()` sends, where `data` is JSON-encoded as `{node, data}`.

export type AgentEventType =
  | "session_started"
  | "node_update"
  | "plan_review_required"
  | "plan_decision_received"
  | "session_completed"
  | "session_failed";

export interface PlanReviewRequiredPayload {
  type: "plan_review";
  plan: ResearchPlan;
  instructions: string;
}

// node_update payloads vary by which node produced them — these are the
// LangGraph node return shapes from app/agents/*.py, loosely typed since
// only a subset of fields is ever present on any given event.
export interface NodeUpdatePayload {
  // supervisor
  plan?: ResearchPlan;
  plan_approved?: boolean;
  // specialist agents (web_search_agent / pdf_agent / code_exec_agent / fact_check_subtask_agent)
  subtask_results?: SubtaskResult[];
  // synthesis_agent
  draft_title?: string;
  draft_summary?: string;
  draft_sections?: {
    heading: string;
    content: string;
    source_indices: number[];
  }[];
  // fact_check_pass
  fact_check_verdicts?: FactCheckVerdict[];
  // citation_formatter
  report?: ResearchReport;
}

export interface ParsedAgentEvent {
  type: AgentEventType;
  node: string | null;
  sequence: number;
  data:
    | PlanReviewRequiredPayload
    | NodeUpdatePayload
    | ResearchReport
    | { error: string }
    | { query: string }
    | Record<string, unknown>;
}
