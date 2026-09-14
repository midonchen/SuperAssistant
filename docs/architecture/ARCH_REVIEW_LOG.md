# Architecture Review Log

## 2026-03-31 - MVP Baseline Bootstrap

- Decision: Monorepo with `apps/mobile`, `apps/admin`, `services/api`, `packages/contracts`, `infra`.
- Reason: Faster MVP integration and unified governance gates.
- Module Boundaries: `auth`, `inventory`, `voice`, `ocr`, `push`, `admin`.
- Public Interfaces: API contracts frozen under `packages/contracts/openapi/openapi.v1.yaml`.
- Rollback Strategy: Keep API changes backward-compatible using `X-API-Revision`; block breaking changes in CI review.

## 2026-03-31 - Phase 1 Persistence Baseline

- Decision: Replace in-memory state for `auth/session/user/inventory/log` with SQLAlchemy-backed persistence.
- Scope:
  - Added SQLAlchemy models and DB engine bootstrap.
  - Added Alembic init + first migration (`20260331_0001`).
  - Kept suggestion/audit task memory model temporarily to reduce migration risk.
- Compatibility: API response contracts unchanged.
- Risk: Mixed persistence model (DB + memory) until next phase.
- Mitigation: Keep boundaries explicit in `core/store.py`, migrate suggestion/audit in Phase 2.

## 2026-03-31 - Phase 2 Persistence (Suggestion + Audit)

- Decision: Persist `purchase_suggestions` and `audit_tasks` into DB tables.
- Added models: `SuggestionModel`, `SuggestionItemModel`, `AuditTaskModel`.
- Added Alembic revision: `20260331_0002`.
- API compatibility: Existing endpoints unchanged (`/suggestions/*`, `/admin/audit/*`).
- Benefit: Removes in-memory state loss across restarts and enables consistent admin audit workflow.

## 2026-03-31 - Phase 3 Jobs and Push Persistence

- Decision: Introduce Celery + Redis for scheduled jobs (auto decay, purchase reminders).
- Added DB tables: `push_devices`, `push_preferences`, `push_deliveries`.
- Added Alembic revision: `20260331_0003`.
- Push endpoints now persist devices/preferences; reminder runs produce delivery records for observability.
- Dashboard KPI extended with push sent/failed counters.

## 2026-03-31 - Offline Replay and Conflict Engine

- Decision: Add Redis-backed offline replay queue with local in-process fallback for non-redis/test environments.
- Implemented `op_id` idempotent replay marker and `client_version` conflict checks in batch inventory ops.
- Added endpoint: `POST /api/v1/inventory/offline/replay` for enqueuing client offline operations.
- Added Celery minutely task for replay queue processing.
- Conflict response standardized to `BIZ_409_CONFLICT` with `server_version`/`client_version` details.

## 2026-03-31 - Phase 4 Admin API Integration

- Decision: Integrate Next.js admin pages directly with backend API contracts using client-side token session.
- Implemented pages: Dashboard / Users / Audit with live fetch and actions.
- Auth approach: Admin stores `access_token` in browser localStorage for MVP internal usage.
- Required headers (`X-Request-Id`, `X-App-Version`, `X-Platform`, `Idempotency-Key`) are enforced by shared web admin API client.
- Tradeoff: Token bootstrap via SMS login panel is operationally simple for MVP but not production-grade SSO.

## 2026-03-31 - Phase 5 Mobile Screen Integration

- Decision: Upgrade Flutter app from placeholder pages to state-driven MVP screens aligned with PRD chapter 12 wireframe flows.
- Implemented routes: Auth, Onboarding, Home, List, Log, Settings, Voice Modal, OCR Modal, Manual Fill, Item Detail.
- Introduced in-app `AppStore` for shared inventory/suggestion/log state across screens.
- Added interaction coverage:
  - Home inventory grid + long-press quick calibrate to voice modal
  - List filter sheet + suggestion generation
  - Log search/filter + detail bottom sheet
  - Settings save flow + max stock updates
  - Voice/OCR modal state machines with confirm actions
- Tradeoff: Uses mock/in-memory mobile store for now; API integration is a later step.

## 2026-03-31 - Phase 5 Mobile API Integration

- Decision: Start replacing in-app mobile mock state with backend API-backed store while keeping graceful fallback behavior.
- Implemented mobile API client for auth, inventory, logs, suggestions, batch operations, and push preference.
- Auth screen now performs real SMS send/login calls; app store refreshes server data post-login.
- Inventory operations now optimistic-update locally and sync via `/inventory/operations/batch`.
- Tradeoff: token persistence remains in-memory (app-runtime only) for MVP; secure storage deferred.

## 2026-03-31 - Phase 5 Mobile AI Parse Integration

- Decision: Replace mobile simulated Voice/OCR parse flows with backend `/ai/*` contract calls and confirm-write path.
- Added client calls for:
  - `POST /api/v1/ai/voice/parse`
  - `POST /api/v1/ai/ocr/parse`
  - `POST /api/v1/ai/parse/confirm`
- Updated mobile parse entity model to carry `parse_session_id` and full confirm payload fields required by `ParsedEntity`.
- Updated Voice/OCR screens to:
  - call live parse APIs
  - keep UI state machine behavior (success/low-confidence/failure/partial)
  - confirm via backend and refresh inventory/log snapshot
- Tradeoff: voice calibrate sub-flow keeps a local fallback parse shape until dedicated calibrate-aware parse contract is added.

## 2026-03-31 - Phase 5 Mobile Session Hardening

- Decision: Add persistent mobile auth session and silent token refresh before entering Phase 6 integration.
- Implemented:
  - `shared_preferences`-based persistence for `access_token`, `refresh_token`, `session_id`, `device_id`.
  - App startup hydration path on Auth screen (`initializeSession`) with auto redirect on valid session.
  - `ApiClient` 401 handling for `AUTH_401_TOKEN_EXPIRED` with one-time refresh + request retry.
  - Runtime session callbacks to keep persisted tokens in sync after login/refresh/logout.
  - Settings page logout action to revoke current session and clear local auth state.
- Tradeoff: token storage is plaintext in app preferences for MVP speed; secure enclave/keychain migration remains post-MVP hardening work.

## 2026-03-31 - Phase 5 Auth Failure UX Guard

- Decision: Enforce unified redirect-to-auth behavior on protected screens when session is invalid.
- Implemented:
  - `MainTabScaffold` now guards authenticated pages and redirects to `/auth` when `isAuthenticated == false`.
  - Added standardized user feedback via Snackbar on redirect (`登录已过期，请重新登录` or `请先登录`).
  - `AppStore` now writes explicit auth-expired error when silent refresh fails.
  - Auth screen now surfaces previous auth error after startup session check.
- Tradeoff: current guard is view-layer based (tab scaffolds); deeper route-level guard for all pages can be added in a dedicated navigation layer later.

## 2026-03-31 - Phase 5 Secure Session Storage + Full Route Guard

- Decision: Upgrade token persistence to secure storage and expand auth guard from tab pages to all protected routes.
- Implemented:
  - Replaced mobile session persistence backend with `flutter_secure_storage` (Keychain-backed on iOS).
  - Added reusable `AuthGuard` widget and applied it to all protected routes in `AppRoutes`.
  - Removed duplicate auth guard logic from `MainTabScaffold` to avoid repeated redirects/snackbars.
- Tradeoff: secure storage migration is done at code level; device-level verification requires running on real iOS environment in Phase 6联调.

## 2026-03-31 - Refresh Session Consistency Fix

- Decision: Keep `session_id` stable during token refresh and rotate tokens in-place on the existing session.
- Implemented:
  - Added `store.rotate_session_tokens_by_refresh(...)` to update `access_token` + `refresh_token` on the same session row.
  - Updated `/auth/token/refresh` to return `session_id` together with rotated tokens.
  - Enforced bearer auth on `/auth/logout` to match contract security.
  - Updated mobile API refresh handling to accept `session_id` from refresh response.
- Risk reduced: avoids "refresh created hidden new session" mismatch that could break logout/session tracking semantics.

## 2026-03-31 - Mobile Offline Replay Integration

- Decision: Wire mobile batch-write failures to backend offline replay queue for eventual consistency.
- Implemented:
  - Added typed API error handling in mobile client (`ApiRequestException`).
  - Added mobile API call for `POST /api/v1/inventory/offline/replay`.
  - `AppStore` now buffers failed batch ops locally and flushes them to backend replay queue after successful refresh/auth recovery.
  - Added conflict-specific branch for `BIZ_409_CONFLICT` to auto-refresh snapshot instead of blind replay queueing.
  - Home briefing now shows pending replay queue count for operator visibility.
- Tradeoff: local pending replay queue is in-memory only (cleared on app restart); durable offline queue persistence can be added in follow-up.

## 2026-03-31 - Mobile Offline Replay Durability

- Decision: Persist pending mobile offline replay jobs to survive app restart/device process kill.
- Implemented:
  - Added secure-storage key `mobile.sync.pending_offline_ops`.
  - Added queue serialize/deserialize on `AppStore` (`jsonEncode/jsonDecode`).
  - Queue now loads during session initialization and flushes to backend when auth/data refresh succeeds.
  - Queue persistence clears only on explicit logout-reset flow.
- Tradeoff: JSON blob persistence is simple but non-transactional; if queue volume grows, switch to SQLite-based local queue.

## 2026-03-31 - Logout Ownership Guard

- Decision: Enforce that `/auth/logout` can only revoke the caller's own session.
- Implemented:
  - Added `store.revoke_session_owned(session_id, user_id)` user-bound revoke method.
  - Updated auth logout route to use user-bound revoke and return actual revoke result.
  - Added regression test for cross-user session revoke attempt.
- Risk reduced: prevents token holder from revoking arbitrary session IDs belonging to other users.

## 2026-03-31 - Phase 5 Acceptance Automation

- Decision: Add a single command to execute governance gates plus key Phase 5 acceptance scenarios.
- Implemented:
  - Added script `scripts/run_phase5_acceptance.sh`.
  - Added `make phase5-accept` target.
  - Added README runbook entry for Phase 5 acceptance execution.
- Benefit: reduces manual QA handoff ambiguity and prepares repeatable pre-Phase6 checks.

## 2026-03-31 - Admin RBAC Baseline Gate

- Decision: Restrict all `/admin/*` endpoints to allowlisted admin principals only, instead of any authenticated user.
- Implemented:
  - Added `require_admin` dependency on top of bearer auth.
  - Added store-level admin principal check (`SUPERASSISTANT_ADMIN_PHONES`, default includes `13900139000`).
  - Applied admin dependency to Dashboard/Users/Audit endpoints.
  - Added API regression tests for non-admin 403 rejection and admin success path.
  - Updated OpenAPI admin routes with explicit `403` response.
- Tradeoff: this is an allowlist baseline gate, not a full role matrix with hierarchical permissions.

## 2026-03-31 - Session Cap + Security Event Trail

- Decision: Enforce multi-device session cap at login time and persist eviction events for security traceability.
- Implemented:
  - Added max active session cap (`SUPERASSISTANT_MAX_ACTIVE_SESSIONS`, default `3`).
  - During login session creation, oldest active sessions are revoked when cap is exceeded.
  - Added `security_events` table + model for session governance traces.
  - Added `SESSION_EVICTED` event records with reason, evicted session ID, and cap details.
  - Added regression test validating oldest-session eviction + security event persistence.
- Tradeoff: events are currently DB-tracked for backend audit/testing and not yet exposed as dedicated admin query API.

## 2026-03-31 - Admin Action Audit Trail

- Decision: Persist security audit events for core admin actions to satisfy governance traceability.
- Implemented:
  - Added `store.add_security_event(...)` for reusable admin/security event writes.
  - Added audit writes for:
    - `POST /admin/users/{user_id}/session/revoke` -> `ADMIN_REVOKE_USER_SESSIONS`
    - `POST /admin/audit/tasks/{task_id}/review` -> `ADMIN_AUDIT_REVIEW`
  - Extended API tests to verify admin action events are written with key details (`target_user_id`, `task_id`, `action`).
- Benefit: backend governance actions now have persistent audit trail tied to the operator user.

## 2026-03-31 - CI Migration Gate on PostgreSQL

- Decision: Enforce migration health in CI against real PostgreSQL service before API test run.
- Implemented:
  - Added Postgres service in `.github/workflows/ci.yml`.
  - Added CI step `alembic upgrade head` with PostgreSQL `DATABASE_URL`.
  - Kept governance checks and API tests after migration gate.
- Benefit: schema drift/migration breakage is caught early in pipeline, not deferred to manual staging checks.

## 2026-03-31 - Phase 6 Performance Smoke Baseline

- Decision: Add a lightweight, repeatable perf gate script aligned with MVP thresholds before full benchmark platform rollout.
- Implemented:
  - Added `scripts/run_phase6_perf_smoke.py` covering:
    - voice parse p95 target (`<=1200ms`)
    - OCR parse p95 target (`<=2800ms`)
    - offline replay throughput for 100 jobs (`<=30s`)
  - Added `make phase6-perf` entrypoint.
  - Fixed OCR confirm snapshot path to use DB-backed item listing (removed stale in-memory reference).
  - Added regression test for `/ai/parse/confirm` inventory snapshot response.
- Tradeoff: this is a local smoke baseline using `TestClient`, not yet an external-load, distributed benchmark harness.

## 2026-03-31 - RBAC Role Matrix Baseline (USER/ADMIN/AUDITOR)

- Decision: Replace single admin allowlist gate with explicit user roles to support differentiated permissions.
- Implemented:
  - Added `users.role` schema field and migration (`20260331_0005_user_roles`).
  - Role resolution by phone allowlist at login bootstrap:
    - `SUPERASSISTANT_ADMIN_PHONES` -> `ADMIN`
    - `SUPERASSISTANT_AUDITOR_PHONES` -> `AUDITOR`
    - fallback -> `USER`
  - Added role-aware auth deps:
    - `require_admin` for `/admin/dashboard` and `/admin/users*`
    - `require_audit_reviewer` for `/admin/audit/*` (`ADMIN|AUDITOR`)
  - Added regression tests for auditor access boundary and updated admin UI user table to display role.
- Tradeoff: approval workflow and fine-grained action-level policy remain follow-up work.

## 2026-03-31 - AI Pipeline Provider Abstraction Baseline

- Decision: Introduce explicit STT/OCR/LLM provider abstraction before wiring real external provider APIs.
- Implemented:
  - Added `core/ai_pipeline.py` with provider interfaces and runtime pipeline:
    - `STTProvider`
    - `OCRTextProvider`
    - `EntityParser`
  - Added compatibility parser adapters:
    - `ClaudeCompatibleParser`
    - `GPTCompatibleParser`
  - Added route integration for `/ai/voice/parse` and `/ai/ocr/parse` via shared `ai_pipeline`.
  - Parse session ID generation is now per-request (`parse-v-*`, `parse-o-*`) and propagated to all entities.
  - Added API regression test for parse session/entity contract and pipeline behavior.
- Tradeoff: external Whisper/Claude/GPT network calls are not enabled yet; current adapters are deterministic local fallback with env-selectable compatibility mode.

## 2026-03-31 - Phase 6 Release Readiness Gate Script

- Decision: Provide one-command pre-release gate to reduce manual遗漏 before UAT/gray release.
- Implemented:
  - Added `scripts/run_phase6_release_readiness.sh`.
  - Added `make phase6-ready` entrypoint.
  - Gate flow includes:
    - governance checks
    - full API regression tests
    - Phase 5 acceptance subset
    - Phase 6 perf smoke baseline
- Benefit: release-readiness checks are now repeatable and can be run by any team member with consistent output.

## 2026-03-31 - External AI Provider Integration with Fallback

- Decision: Enable real provider calls behind env-gated adapters while keeping deterministic local fallback for reliability.
- Implemented:
  - Added OpenAI Whisper adapter for STT (`OpenAIWhisperProvider`) with remote audio fetch + multipart transcription call.
  - Added Anthropic Claude parser adapter (`AnthropicClaudeParser`) and OpenAI GPT parser adapter (`OpenAIGPTParser`) for entity extraction.
  - Added robust parser output normalization/validation (`_extract_json`, `_to_entities`) to preserve contract safety.
  - Enabled runtime selection via env vars:
    - `STT_PROVIDER=openai|local`
    - `LLM_PROVIDER=claude|gpt`
    - `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
  - Added fail-safe fallback on provider errors back to local heuristic parser/STT.
  - Added dedicated unit tests for external adapter parsing and fallback behavior.
- Tradeoff: current observability is log-based; provider-level metrics, rate-limit tracking, and circuit-breaker policies remain follow-up.

## 2026-03-31 - LLM Provider Switch to DeepSeek

- Decision: Set DeepSeek as the default LLM provider for inventory entity parsing while preserving fallback safety.
- Implemented:
  - Added `DeepSeekParser` adapter using DeepSeek Chat Completions endpoint.
  - Added `DeepSeekCompatibleParser` with env-based activation and fallback to heuristic parser.
  - Changed parser default selection to `LLM_PROVIDER=deepseek`.
  - Added DeepSeek adapter unit test with mocked external response.
  - Updated API runtime documentation for:
    - `DEEPSEEK_API_KEY`
    - `DEEPSEEK_MODEL`
    - `DEEPSEEK_CHAT_ENDPOINT`
- Security note: API keys are runtime env vars only and are not hardcoded into repository files.

## 2026-03-31 - AI Provider Runtime Metrics + Circuit Breaker

- Decision: Add runtime guardrails for external AI provider instability without blocking user flows.
- Implemented:
  - Added runtime metrics in AI pipeline:
    - request counts (voice/ocr)
    - external call counts/failures
    - fallback counts
    - breaker-skip counts
    - last provider errors
  - Added circuit breakers for STT/parser external calls:
    - configurable failure threshold + cooldown window
    - automatic fallback to local STT / heuristic parser when open
  - Exposed `ai_runtime` metrics in `/admin/dashboard/summary`.
  - Added regression tests for breaker-open skip behavior and dashboard metric exposure.
- Tradeoff: metrics are in-process memory counters; cross-instance aggregation requires external telemetry backend later.

## 2026-03-31 - High-Risk Admin Approval Workflow Baseline

- Decision: Replace direct execution of high-risk admin session revocation with mandatory approval flow.
- Implemented:
  - Added `approval_requests` data model and migration.
  - Added approval store with:
    - create request
    - list requests
    - review request (approve/reject)
    - approve-path execution for `REVOKE_USER_SESSIONS`
  - Enforced no self-approval for approve actions.
  - Added admin APIs:
    - `POST /admin/users/{user_id}/session/revoke` (create approval)
    - `GET /admin/approvals`
    - `POST /admin/approvals/{approval_id}/review`
  - Added admin web page `/approvals` and updated Users page to submit revoke requests.
  - Added security audit events:
    - `ADMIN_APPROVAL_REQUEST_CREATED`
    - `ADMIN_APPROVAL_REVIEWED`
- Tradeoff: baseline is single-stage approval; multi-step chain, SLA escalation, and notification routing remain future work.

## 2026-04-01 - Provider Quota Guardrails (QPS/Token Budget)

- Decision: Add quota-level runtime protection on external AI providers to prevent runaway cost and burst failure.
- Implemented:
  - Added `core/ai_quota.py` with `ProviderQuotaGuard`.
  - Added three quota dimensions:
    - requests per minute
    - tokens per minute
    - tokens per day
  - Added Redis-backed shared counters (`AI_QUOTA_REDIS_URL`) with local in-process fallback when Redis is unavailable.
  - Integrated quota checks in AI pipeline before external STT/parser calls and fallback to local path when rejected.
  - Exposed quota snapshot and rejection metrics in admin `ai_runtime`.
  - Added regression tests for quota rejection + fallback continuity.
- Tradeoff: local fallback counters are per-process and only suitable for dev/single-instance use.

## 2026-04-01 - Phase 6 External-Load Benchmark Suite

- Decision: Add a real HTTP concurrency benchmark suite to complement local `TestClient` perf smoke.
- Implemented:
  - Added `scripts/run_phase6_external_load.py`.
  - Script starts standalone API server process, executes concurrent HTTP scenarios, and enforces p95/error thresholds.
  - Covered scenarios:
    - `GET /api/v1/inventory/items` (home first-screen API proxy)
    - `POST /api/v1/ai/voice/parse`
    - `POST /api/v1/ai/ocr/parse`
    - `POST /api/v1/inventory/offline/replay` 100-op enqueue timing
  - Added `make phase6-load` command and runbook references.
- Tradeoff: this suite validates external HTTP and application behavior on a single-node process; full distributed benchmark (multi-node + network shaping) remains a future scaling stage.

## 2026-04-01 - Phase 6 UAT + Gray Release Package

- Decision: Convert Phase 6 release preparation from ad-hoc notes into mandatory release artifacts with a single verification command.
- Implemented:
  - Added release docs:
    - `docs/release/UAT_EXECUTION_CHECKLIST.md`
    - `docs/release/GRAY_RELEASE_RUNBOOK.md`
    - `docs/release/RELEASE_SIGNOFF_TEMPLATE.md`
  - Added `scripts/run_phase6_release_pack.sh` to enforce:
    - release-doc completeness
    - `phase6-ready` gate pass
    - `phase6-load` gate pass
  - Added `make phase6-pack` command as pre-release package gate.
- Tradeoff: this establishes execution templates and gates; real staging/prod rollout evidence must still be produced in the release window.

## 2026-04-01 - Phase 6 Release Evidence Automation

- Decision: Standardize release evidence generation into reproducible markdown artifacts rather than manual copy-paste.
- Implemented:
  - Added `scripts/generate_phase6_release_evidence.sh`.
  - Added `make phase6-evidence` command.
  - Report now includes:
    - UTC timestamp
    - host/runtime metadata
    - full output of `make phase6-pack`
    - final PASS/FAIL summary
  - Output location standardized under `docs/release/evidence/`.
  - Added mobile runtime endpoint matrix in `apps/mobile/README.md` for simulator/device/staging consistency.
- Tradeoff: script captures local/staging execution evidence only; production rollout evidence still depends on live window execution and owner signoff.

## 2026-04-01 - Gray Wave Checkpoint Logging Automation

- Decision: Make each gray-release wave produce a structured checkpoint record with optional live backend metrics snapshot.
- Implemented:
  - Added `scripts/record_gray_wave_checkpoint.py`.
  - Added two operating modes:
    - `template`: generate checkpoint file before wave starts
    - `live`: collect `dashboard/approvals/audit` snapshot from admin APIs
  - Added make entrypoints:
    - `make phase6-wave-template WAVE=10|50|100`
    - `make phase6-wave-live WAVE=10|50|100 API_BASE_URL=...`
  - Added evidence naming standard:
    - `docs/release/evidence/GRAY_WAVE_<wave>_<timestamp>.md`
  - Updated release runbook and signoff template to include wave evidence files.
- Tradeoff: live mode depends on reachable API and admin role bootstrap; production window data still requires real operator execution.

## 2026-04-01 - Release Signoff Draft Compilation

- Decision: Auto-compile a signoff draft from latest evidence files to minimize manual整理 before GO/NO-GO meeting.
- Implemented:
  - Added `scripts/generate_release_signoff_draft.py`.
  - Added `make phase6-signoff-draft`.
  - Script compiles:
    - latest `PHASE6_RELEASE_EVIDENCE_*.md`
    - latest wave logs for `10/50/100`
  - Output:
    - `docs/release/evidence/RELEASE_SIGNOFF_DRAFT_<timestamp>.md`
  - Updated release template and runbook references.
- Tradeoff: draft reflects file availability/status only; owner decisions and production incident context still require human signoff.

## 2026-04-01 - Release Window Readiness Gate

- Decision: Add explicit soft/strict readiness checks for release-window artifacts to avoid subjective GO判断.
- Implemented:
  - Added `scripts/check_release_window_readiness.py`.
  - Added commands:
    - `make phase6-window-status` (always produces report)
    - `make phase6-window-gate` (strict, non-zero on missing readiness)
  - Strict gate criteria:
    - latest `PHASE6_RELEASE_EVIDENCE` is PASS
    - required wave logs (10/50/100) exist and are `mode=live` + `snapshot=OK`
    - signoff draft exists
  - Added standardized output:
    - `docs/release/evidence/RELEASE_WINDOW_STATUS_<timestamp>.md`
- Tradeoff: gate validates artifact and snapshot completeness, not business acceptance decisions themselves.

## 2026-04-01 - Local Release Simulation Flow

- Decision: Provide a single local rehearsal command to execute the full release evidence chain end-to-end.
- Implemented:
  - Added `scripts/run_phase6_local_release_simulation.sh`.
  - Added `make phase6-local-sim`.
  - Command flow:
    - starts local API process
    - runs `phase6-pack`
    - generates phase6 evidence
    - records live wave logs for 10/50/100
    - generates signoff draft
    - executes strict window gate
- Tradeoff: this validates process readiness in local environment; production decision still depends on actual staging/prod rollout data.

## 2026-04-01 - Release Handoff Package Builder

- Decision: Generate a single handoff bundle containing latest release evidence and required signoff docs.
- Implemented:
  - Added `scripts/build_release_handoff_package.py`.
  - Added `make phase6-handoff-pack`.
  - Default behavior validates strict window readiness before packaging.
  - Package outputs:
    - folder: `docs/release/handoff/RELEASE_HANDOFF_<timestamp>/`
    - archive: `docs/release/handoff/RELEASE_HANDOFF_<timestamp>.tar.gz`
    - manifest: `MANIFEST.md`
- Tradeoff: package reflects latest local artifact set; operators still need to attach external incident/ticket context if required by org release policy.

## 2026-04-01 - Final Signoff Generator

- Decision: Add gate-validated final signoff generation to reduce manual edits on release decision document.
- Implemented:
  - Added `scripts/finalize_release_signoff.py`.
  - Added `make phase6-signoff-final`.
  - Preconditions:
    - latest strict window status must be PASS
    - required wave evidence (10/50/100) must exist
  - Output:
    - `docs/release/evidence/RELEASE_SIGNOFF_FINAL_<timestamp>.md`
  - Enhanced handoff package builder to include latest `RELEASE_SIGNOFF_FINAL` when available.
- Tradeoff: final file still requires human signature decisions in governance process; script focuses on evidence binding and consistency.

## 2026-04-01 - Gray Wave Execution Runner

- Decision: Compress wave-time operational steps into one command per wave to reduce manual runbook errors during release window.
- Implemented:
  - Added `scripts/run_gray_wave_execution.sh`.
  - Added `make` targets:
    - `phase6-wave-exec` (wave execution)
    - `phase6-wave-exec-final` (wave execution + finalize bundle)
  - Runner flow:
    - records live checkpoint for current wave
    - refreshes signoff draft
    - runs strict window gate scoped by wave set
  - optionally finalizes signoff + handoff package
- Tradeoff: runner assumes API reachability and valid admin role bootstrap; cross-team approvals still remain manual governance actions.

## 2026-04-01 - Admin Security Events Query + Console

- Decision: Expose persisted security events through a dedicated admin query API and console page to close governance observability gap.
- Implemented:
  - Added backend query method `core/security_store.py::query_security_events(user_id, event_type, limit)`.
  - Added endpoint `GET /api/v1/admin/security/events`.
  - Permission model uses `require_audit_reviewer` (`ADMIN|AUDITOR`), aligned with audit/approval governance scope.
  - Added admin console page `/security` with filters and event table.
  - Updated OpenAPI contract and added regression tests for RBAC + filtered query contract.
- Tradeoff: event retrieval currently supports exact-match filtering only (`user_id`, `event_type`); time-window and fuzzy search are deferred.

## 2026-04-01 - Gray Wave Auto Gate Evaluator

- Decision: Add machine-evaluated wave promotion gating so rollout cannot progress only by log generation.
- Implemented:
  - Added `scripts/evaluate_gray_wave_gate.py` to evaluate latest wave snapshot against threshold rules.
  - Added decision model:
    - `CONTINUE`: all rules pass
    - `HOLD`: non-critical rules fail
    - `ROLLBACK`: critical rules fail (snapshot/breaker/critical error ratios)
  - Added generated evidence file `GRAY_WAVE_GATE_<wave>_<timestamp>.md`.
  - Integrated evaluator into `run_gray_wave_execution.sh` with `--require-continue`, making wave execution fail-fast when decision is not `CONTINUE`.
  - Added make entrypoint `phase6-wave-gate` with optional strict mode.
- Tradeoff: gate thresholds are static defaults; environment-specific dynamic baselines (e.g., traffic-adjusted limits) remain future optimization.

## 2026-04-01 - Phase Progress Reporter

- Decision: Add a machine-generated progress report so current phase and remaining work can be queried consistently at any time.
- Implemented:
  - Added `scripts/report_phase_status.py`.
  - Report includes:
    - current phase and completed plan-part count
    - roadmap phase map with done/pending markers
    - remaining work from `IMPLEMENTATION_STATUS.md`
    - release evidence snapshot (strict gate + waves 10/50/100 + non-local evidence detection)
  - Added output directory `docs/roadmap/status/` with timestamped reports.
  - Added make entrypoint `phase-status`.
- Tradeoff: current parser relies on markdown conventions in status docs; if section format changes, script rules must be updated accordingly.

## 2026-04-01 - Non-Local Wave Evidence Gate

- Decision: Add explicit non-local evidence enforcement for release-window gate so staging/prod rollout cannot be signed off using localhost-only wave logs.
- Implemented:
  - Extended `check_release_window_readiness.py` with `--require-non-local-wave-evidence`.
  - Wave status now records:
    - `api_base_url`
    - `non_local` boolean
  - Added make target `phase6-window-gate-live` for strict + non-local enforcement.
  - Updated `run_gray_wave_execution.sh` to support `REQUIRE_NON_LOCAL_WAVES=1` and pass the non-local enforcement flag.
- Tradeoff: non-local check is URL-pattern based; it verifies evidence source class (local vs non-local), not end-to-end environment identity ownership.
