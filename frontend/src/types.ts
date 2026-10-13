// Shapes returned by the FastAPI backend (backend/main.py).

export type Role = "boss" | "inventory" | "accounting" | "facilities" | "customer_service";

export type TicketStatus =
  | "open"
  | "in_progress"
  | "waiting_approval"
  | "waiting_customer"
  | "blocked"
  | "resolved";

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  lease_id: number | null;
  invoice_id: number | null;
  status: TicketStatus;
  state: "open" | "resolved";
  notes: string | null;
  created_at: string;
  pending_payment_requests: number;
  customer_drafts: number;
}

export interface RunInfo {
  run_id: string;
  ticket_id: number;
  status: string; // running | done | stopped_budget | stopped_error | cancelled
  started_at: string;
  finished_at: string | null;
  result: BossDecision | { reason?: string; stopped?: string } | null;
}

export interface TicketsResponse {
  date_today: string;
  count: number;
  tickets: Ticket[];
  active_run: RunInfo | null;
}

export interface Fact {
  source_tool: string;
  detail: string;
}

export interface AgentOutput {
  ticket_id: number;
  summary: string;
  facts: Fact[];
  actions_taken: string[];
  needs_human: string[];
  blockers: string[];
  recommendation?: string;
  [key: string]: unknown;
}

export interface BossDecision extends AgentOutput {
  final_status: TicketStatus;
  decision: string;
  agents_consulted: Role[];
  payment_requests_awaiting_human: number[];
  customer_draft_ids: number[];
  follow_ups: string[];
}

export interface ToolCall {
  tool: string;
  args: Record<string, unknown> | string;
}

export interface ToolResult {
  tool: string | null;
  error: boolean;
  content: unknown;
}

export interface FeedEvent {
  seq: number;
  ts: string;
  run_id: string;
  agent_run_id: string | null;
  ticket_id: number | null;
  agent: string; // a Role, or a human's name / "system"
  chain: string[];
  depth: number;
  event: string;
  said: string | null;
  tools: ToolCall[];
  tool_results: ToolResult[];
  tokens_so_far: number | null;
  model: string | null;
  output?: AgentOutput | Record<string, unknown>;
}

export interface EventsResponse {
  last_seq: number;
  count: number;
  events: FeedEvent[];
}

export interface PaymentRequest {
  id: number;
  kind: "invoice" | "rent" | "purchase_order";
  ref_id: number;
  amount: number;
  payee: string;
  account: string;
  ticket_id: number | null;
  reason: string;
  requested_by: Role;
  status: "pending" | "paid" | "rejected" | "refused";
  created_at: string;
  decided_by: string | null;
  decided_at: string | null;
  decision_note: string | null;
  payment_id: number | null;
}

export interface PaymentsResponse {
  status: string;
  count: number;
  requests: PaymentRequest[];
}

export interface Cash {
  account: string;
  balance: number;
  as_of: string;
  pending_total: number;
  available_to_commit: number;
  pending_requests: Pick<PaymentRequest, "id" | "kind" | "ref_id" | "amount" | "payee" | "ticket_id" | "requested_by" | "created_at">[];
  date_today: string;
}

export interface CustomerDraft {
  id: number;
  ticket_id: number;
  recipient: string;
  subject: string;
  body: string;
  author: string;
  status: string;
  created_at: string;
}

export interface TicketDetail {
  date_today: string;
  ticket: Ticket;
  lease: Record<string, unknown> | null;
  invoice: Record<string, unknown> | null;
  work_so_far: {
    log: { id: number; agent: string; entry: string; created_at: string }[];
    payment_requests: PaymentRequest[];
    purchase_orders: Record<string, unknown>[];
    stock_holds: Record<string, unknown>[];
    customer_drafts: CustomerDraft[];
  };
}

export interface ApproveResult {
  request_id: number;
  ticket_id: number | null;
  status: "paid" | "refused";
  reason?: string;
  amount?: number;
  payee?: string;
  balance_before?: number;
  balance_after?: number;
  balance?: number;
}
