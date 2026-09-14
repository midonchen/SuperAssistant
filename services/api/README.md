# SuperAssistant API

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn main:app --reload
```

Optional admin allowlist (for `/admin/*` RBAC):

```bash
export SUPERASSISTANT_ADMIN_PHONES="13900139000"
```

Optional auditor allowlist (can access `/admin/audit/*`, but not `/admin/dashboard` or `/admin/users`):

```bash
export SUPERASSISTANT_AUDITOR_PHONES="13900139001"
```

Optional active-session limit per user (oldest session will be revoked when exceeded):

```bash
export SUPERASSISTANT_MAX_ACTIVE_SESSIONS="3"
```

Optional AI parser compatibility mode (default `deepseek`, fallback-local behavior in MVP):

```bash
export LLM_PROVIDER="deepseek"   # or "claude" / "gpt"
```

Optional STT provider mode (default `local`, set to `openai` to enable Whisper):

```bash
export STT_PROVIDER="openai"
```

Optional external provider credentials (when missing, system auto-falls back to local parsing):

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export DEEPSEEK_API_KEY="sk-..."
```

Optional DeepSeek chat model/endpoint:

```bash
export DEEPSEEK_MODEL="deepseek-chat"
export DEEPSEEK_CHAT_ENDPOINT="https://api.deepseek.com/v1/chat/completions"
```

Optional AI circuit breaker tuning:

```bash
export AI_STT_BREAKER_MAX_FAILURES="3"
export AI_STT_BREAKER_COOLDOWN_SECONDS="30"
export AI_PARSER_BREAKER_MAX_FAILURES="3"
export AI_PARSER_BREAKER_COOLDOWN_SECONDS="30"
```

Optional AI provider quota guardrails (supports Redis-backed multi-instance aggregation):

```bash
export AI_PROVIDER_QPS_PER_MINUTE="120"
export AI_PROVIDER_TOKEN_PER_MINUTE="50000"
export AI_PROVIDER_TOKEN_PER_DAY="1000000"
export AI_QUOTA_REDIS_URL="redis://localhost:6379/3"
```

## Test

```bash
pytest -q
```

## Phase 6 Perf

From repo root, run local smoke and external-load benchmarks:

```bash
make phase-status
make phase6-perf
make phase6-load
make phase6-pack
make phase6-evidence
make phase6-wave-template WAVE=10
make phase6-wave-live WAVE=10 API_BASE_URL=http://localhost:8000/api/v1
make phase6-wave-gate WAVE=10
make phase6-wave-gate WAVE=10 STRICT=1
make phase6-wave-exec WAVE=10 API_BASE_URL=http://localhost:8000/api/v1
make phase6-wave-exec-final WAVE=100 API_BASE_URL=http://localhost:8000/api/v1
make phase6-signoff-draft
make phase6-signoff-final
make phase6-window-status
make phase6-window-gate
make phase6-window-gate-live
make phase6-local-sim
make phase6-handoff-pack
```

## Migrations

```bash
alembic upgrade head
```

## Celery

```bash
celery -A core.celery_app:celery_app worker -l info
celery -A core.celery_app:celery_app beat -l info
```

## Offline Replay

- Enqueue offline ops: `POST /api/v1/inventory/offline/replay`
- Replay processor: Celery task `modules.inventory.domain.tasks.run_offline_replay_queue_task`
- Conflict handling: `BIZ_409_CONFLICT` with `server_version`/`client_version` details

## Admin Approval Workflow (High Risk Ops)

- Submit revoke request: `POST /api/v1/admin/users/{user_id}/session/revoke`
- List approvals: `GET /api/v1/admin/approvals`
- Review approval: `POST /api/v1/admin/approvals/{approval_id}/review`
- Query security events: `GET /api/v1/admin/security/events?user_id=&event_type=&limit=50`
