export type ApiResponse<T> = {
  code: string;
  message: string;
  request_id: string;
  timestamp: string;
  data: T;
};

export type ApiError = {
  code: string;
  message: string;
  request_id: string;
  timestamp: string;
  details?: Record<string, unknown>;
  retriable?: boolean;
};

export type DashboardSummary = {
  kpi: {
    total_users: number;
    total_audit_tasks: number;
    pending_audit_tasks: number;
    push_sent?: number;
    push_failed?: number;
  };
  ai_runtime?: {
    voice_requests?: number;
    ocr_requests?: number;
    stt_external_calls?: number;
    stt_external_failures?: number;
    stt_fallbacks?: number;
    stt_breaker_skips?: number;
    parser_external_calls?: number;
    parser_external_failures?: number;
    parser_fallbacks?: number;
    parser_breaker_skips?: number;
    stt_provider?: string;
    parser_provider?: string;
    stt_breaker_open?: boolean;
    parser_breaker_open?: boolean;
    stt_quota_rejections?: number;
    parser_quota_rejections?: number;
    last_quota_reason?: string;
    quota?: {
      backend?: string;
      limits?: Record<string, number>;
      usage?: Record<string, Record<string, number>>;
    };
  };
  alerts: Array<{ level: string; message: string }>;
};

export type UserRow = {
  user_id: string;
  phone_masked: string;
  timezone: string;
  shopping_day: number;
  shopping_cycle: number;
  role: "USER" | "ADMIN" | "AUDITOR";
  onboarded: boolean;
};

export type AuditTask = {
  task_id: string;
  parse_session_id: string;
  status: string;
  entities: Array<Record<string, unknown>>;
  review_action?: string;
  corrected_entities?: Array<Record<string, unknown>>;
  created_at: string;
  reviewed_at?: string | null;
};

export type LoginResult = {
  session_id: string;
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user_profile: UserRow;
};

export type ApprovalRequest = {
  approval_id: string;
  action_type: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | string;
  target_user_id: string;
  requested_by: string;
  reviewed_by?: string | null;
  request_payload?: Record<string, unknown>;
  review_comment?: string | null;
  execution_result?: Record<string, unknown> | null;
  created_at: string;
  reviewed_at?: string | null;
};

export type SecurityEventRow = {
  event_id: number;
  user_id: string;
  event_type: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type HouseholdMemberRow = {
  user_id: string;
  phone_masked: string;
  role: "OWNER" | "ADMIN" | "MEMBER" | "VIEWER";
  joined_at: string | null;
};

export type HouseholdRow = {
  household_id: string;
  name: string;
  created_by: string;
  created_at: string;
  member_count: number;
  members: HouseholdMemberRow[];
};

export type ReportOverviewRow = {
  household_id: string;
  name: string;
  member_count: number;
  report_count: number;
  total_consumed_qty: number;
  total_wasted_qty: number;
  latest_month: string | null;
};
