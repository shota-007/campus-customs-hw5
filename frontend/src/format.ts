// Small formatting helpers: money, dates, tool calls in plain words.
import type { TicketStatus } from "./types";

export const money = (n: number | undefined | null) =>
  n == null ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD" });

export function islandDate(iso: string | undefined): string {
  if (!iso) return "—";
  const d = new Date(`${iso}T12:00:00`);
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

export function clock(ts: string): string {
  return new Date(ts).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit" });
}

export function duration(fromTs: string, toTs: string): string {
  const s = Math.max(0, Math.round((new Date(toTs).getTime() - new Date(fromTs).getTime()) / 1000));
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;
}

const TOOL_WORDS: Record<string, string> = {
  list_open_tickets: "Scanning the board",
  list_tickets: "Scanning the board",
  get_ticket: "Reading the ticket",
  check_stock: "Checking the shelves",
  check_vendor_status: "Checking on vendors",
  get_lease: "Pulling the lease",
  get_cash_position: "Counting the till",
  quote_bulk_price: "Pricing a bulk deal",
  list_payment_requests: "Reviewing payment requests",
  log_ticket_note: "Writing in the ticket log",
  set_ticket_status: "Making the final call",
  hold_stock: "Setting stock aside",
  release_stock_hold: "Putting stock back",
  draft_purchase_order: "Drafting a purchase order",
  request_payment: "Asking you to approve a payment",
  save_customer_draft: "Writing a customer draft",
  delegate: "Handing off",
  final_result: "Wrapping up",
};

export const toolWords = (tool: string) => TOOL_WORDS[tool] ?? tool.replace(/_/g, " ");

export function toolCall(tool: string, args: Record<string, unknown> | string): string {
  if (typeof args === "string") return `${tool}(${args.slice(0, 80)})`;
  const parts = Object.entries(args)
    .filter(([k]) => k !== "agent" && k !== "task" && k !== "body")
    .map(([k, v]) => {
      const text = typeof v === "string" ? v : JSON.stringify(v);
      return `${k}=${text.length > 40 ? text.slice(0, 40) + "…" : text}`;
    });
  return `${tool}(${parts.join(", ")})`;
}

export const STATUS_LABEL: Record<TicketStatus, string> = {
  open: "Open",
  in_progress: "Crew working",
  waiting_approval: "Awaiting your OK",
  waiting_customer: "Waiting on customer",
  blocked: "Blocked",
  resolved: "All done",
};

/** Board label: the Boss's recorded status, but don't say "awaiting your OK" once nothing is waiting. */
export function boardStatus(t: { status: TicketStatus; pending_payment_requests: number }): string {
  if (t.status === "waiting_approval" && t.pending_payment_requests === 0) return "Approved · nothing waiting";
  return STATUS_LABEL[t.status];
}

export const TYPE_LABEL: Record<string, { icon: string; label: string }> = {
  customer_order: { icon: "👕", label: "Customer order" },
  rent_notice: { icon: "🏠", label: "Rent notice" },
  price_override: { icon: "🏷️", label: "Discount request" },
};

export const KIND_LABEL: Record<string, { icon: string; label: string }> = {
  rent: { icon: "🏠", label: "Rent" },
  invoice: { icon: "🧾", label: "Vendor invoice" },
  purchase_order: { icon: "📦", label: "Purchase order" },
};

export function pretty(value: unknown): string {
  if (typeof value === "string") {
    try {
      return JSON.stringify(JSON.parse(value), null, 2);
    } catch {
      return value;
    }
  }
  return JSON.stringify(value, null, 2);
}
