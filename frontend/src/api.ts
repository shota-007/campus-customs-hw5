// Thin client for the FastAPI backend. Every shop read/write goes through these routes.
import type {
  ApproveResult,
  Cash,
  EventsResponse,
  PaymentsResponse,
  RunInfo,
  TicketDetail,
  TicketsResponse,
} from "./types";

export const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (body as { detail?: unknown }).detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg).join("; ")
          : `HTTP ${res.status}`;
    throw new ApiError(res.status, message);
  }
  return body as T;
}

export const api = {
  tickets: () => request<TicketsResponse>("/tickets"),
  ticket: (id: number) => request<TicketDetail>(`/tickets/${id}`),
  runTicket: (id: number) => request<RunInfo>(`/tickets/${id}/run`, { method: "POST" }),
  run: (runId: string) => request<RunInfo>(`/runs/${runId}`),
  events: (after: number, limit = 1000) => request<EventsResponse>(`/events?after=${after}&limit=${limit}`),
  payments: (status: "pending" | "paid" | "rejected" | "refused" | "all" = "pending") =>
    request<PaymentsResponse>(`/payments?status=${status}`),
  approve: (id: number, approvedBy: string) =>
    request<ApproveResult>(`/payments/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }),
  reject: (id: number, rejectedBy: string, reason: string) =>
    request<{ request_id: number; status: string }>(`/payments/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ rejected_by: rejectedBy, reason }),
    }),
  cash: () => request<Cash>("/cash"),
  reset: () => request<{ ok: boolean; summary: string; balance: number }>("/reset", { method: "POST" }),
};
