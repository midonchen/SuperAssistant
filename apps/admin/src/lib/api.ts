import { API_BASE_URL, APP_VERSION } from "./config";
import type {
  ApiError,
  AnalyticsSnapshot,
  ApiResponse,
  ApprovalRequest,
  AuditTask,
  DashboardSummary,
  HouseholdRow,
  LoginResult,
  ReportOverviewRow,
  SecurityEventRow,
  UserRow,
} from "../types/admin";

type RequestMethod = "GET" | "POST" | "PUT" | "DELETE";

type RequestOptions = {
  method?: RequestMethod;
  token?: string;
  body?: unknown;
  includeIdempotency?: boolean;
};

function requestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}`;
}

function idempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `op-${crypto.randomUUID()}`;
  }
  return `op-${Date.now()}`;
}

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Request-Id": requestId(),
    "X-App-Version": APP_VERSION,
    "X-Platform": "web-admin",
  };

  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }
  if (options.includeIdempotency || method !== "GET") {
    headers["Idempotency-Key"] = idempotencyKey();
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });

  if (!response.ok) {
    let err: ApiError | undefined;
    try {
      err = (await response.json()) as ApiError;
    } catch {
      throw new Error(`HTTP ${response.status}`);
    }
    throw new Error(`${err.code}: ${err.message}`);
  }

  const json = (await response.json()) as ApiResponse<T>;
  return json.data;
}

export async function loginBySms(phone: string, code: string, deviceId: string): Promise<LoginResult> {
  return apiRequest<LoginResult>("/auth/sms/login", {
    method: "POST",
    includeIdempotency: true,
    body: {
      phone,
      code,
      device_id: deviceId,
    },
  });
}

export async function getDashboardSummary(token: string): Promise<DashboardSummary> {
  return apiRequest<DashboardSummary>("/admin/dashboard/summary", { token });
}

export async function getUsers(token: string, phone?: string, userId?: string): Promise<{ list: UserRow[]; total: number }> {
  const params = new URLSearchParams();
  if (phone) {
    params.set("phone", phone);
  }
  if (userId) {
    params.set("user_id", userId);
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return apiRequest<{ list: UserRow[]; total: number }>(`/admin/users${suffix}`, { token });
}

export async function requestRevokeUserSessions(token: string, userId: string, reason?: string): Promise<{ approval_request: ApprovalRequest }> {
  return apiRequest<{ approval_request: ApprovalRequest }>(`/admin/users/${encodeURIComponent(userId)}/session/revoke`, {
    method: "POST",
    token,
    includeIdempotency: true,
    body: { reason: reason ?? "" },
  });
}

export async function getApprovalRequests(
  token: string,
  status?: string,
  actionType?: string
): Promise<{ list: ApprovalRequest[]; total: number }> {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  if (actionType) {
    params.set("action_type", actionType);
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return apiRequest<{ list: ApprovalRequest[]; total: number }>(`/admin/approvals${suffix}`, { token });
}

export async function reviewApprovalRequest(
  token: string,
  approvalId: string,
  decision: "APPROVE" | "REJECT",
  comment?: string
): Promise<{ approval_request: ApprovalRequest } | { approval_id: string; status: string }> {
  return apiRequest<{ approval_request: ApprovalRequest } | { approval_id: string; status: string }>(
    `/admin/approvals/${encodeURIComponent(approvalId)}/review`,
    {
      method: "POST",
      token,
      includeIdempotency: true,
      body: { decision, comment: comment ?? "" },
    }
  );
}

export async function getAuditTasks(token: string): Promise<{ list: AuditTask[]; total: number }> {
  return apiRequest<{ list: AuditTask[]; total: number }>("/admin/audit/tasks", { token });
}

export async function reviewAuditTask(
  token: string,
  taskId: string,
  action: "APPROVE" | "REJECT" | "CORRECT"
): Promise<{ task_id: string; status: string }> {
  return apiRequest<{ task_id: string; status: string }>(`/admin/audit/tasks/${encodeURIComponent(taskId)}/review`, {
    method: "POST",
    token,
    includeIdempotency: true,
    body: { action },
  });
}

export async function getSecurityEvents(
  token: string,
  userId?: string,
  eventType?: string,
  limit: number = 50
): Promise<{ list: SecurityEventRow[]; total: number }> {
  const params = new URLSearchParams();
  if (userId) {
    params.set("user_id", userId);
  }
  if (eventType) {
    params.set("event_type", eventType);
  }
  params.set("limit", String(limit));
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return apiRequest<{ list: SecurityEventRow[]; total: number }>(`/admin/security/events${suffix}`, { token });
}

export async function getHouseholds(token: string): Promise<{ list: HouseholdRow[]; total: number }> {
  return apiRequest<{ list: HouseholdRow[]; total: number }>("/admin/households", { token });
}

export async function getReportOverview(token: string): Promise<{ list: ReportOverviewRow[]; total: number }> {
  return apiRequest<{ list: ReportOverviewRow[]; total: number }>("/admin/reports/overview", { token });
}

export async function getAnalytics(token: string, eventType?: string, limit?: number): Promise<AnalyticsSnapshot> {
  const params = new URLSearchParams();
  if (eventType) {
    params.set("event_type", eventType);
  }
  if (limit) {
    params.set("limit", String(limit));
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return apiRequest<AnalyticsSnapshot>(`/admin/analytics${suffix}`, { token });
}
