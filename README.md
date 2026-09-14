# SuperAssistant Monorepo

This repository implements the SuperAssistant MVP baseline defined in:

- `SuperAssistant_PRD_v1.1.md`
- `交付物01_API字段级JSON示例附录_v1.1.md`
- `交付物02_UI线框清单附录_v1.1.md`

## Monorepo Layout

- `apps/mobile`: Flutter iOS client skeleton
- `apps/admin`: Next.js admin skeleton (Dashboard/Users/Audit)
- `services/api`: FastAPI backend
- `packages/contracts`: OpenAPI + JSON schemas + error codes
- `infra`: Local/staging infrastructure assets
- `docs`: Architecture, process, and roadmap docs

## Governance Gates

- Max handwritten file size: 800 lines
- Module boundaries check for backend modules
- Architecture review artifact requirement for major changes

Run checks:

```bash
npm run check:all
```

Run API tests:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e services/api[dev]
pytest -q services/api/tests
```

Generate current phase progress and remaining-work report:

```bash
make phase-status
```

Run Phase 5 acceptance (governance + key session/offline/admin flows):

```bash
make phase5-accept
```

Run Phase 6 perf smoke baseline (voice/OCR p95 + 100-job replay throughput):

```bash
make phase6-perf
```

Run Phase 6 external-load benchmark suite (real HTTP concurrency against standalone API process):

```bash
make phase6-load
```

Run Phase 6 release readiness gate (checks + regression + acceptance + perf):

```bash
make phase6-ready
```

Run Phase 6 release pack gate (release-ready + external-load + required release docs):

```bash
make phase6-pack
```

Generate Phase 6 release evidence report (includes full gate output in markdown):

```bash
make phase6-evidence
```

Record gray wave checkpoints (template/live):

```bash
make phase6-wave-template WAVE=10
make phase6-wave-live WAVE=10 API_BASE_URL=http://localhost:8000/api/v1
make phase6-wave-gate WAVE=10
make phase6-wave-gate WAVE=10 STRICT=1
make phase6-wave-exec WAVE=10 API_BASE_URL=http://localhost:8000/api/v1
make phase6-wave-exec-final WAVE=100 API_BASE_URL=http://localhost:8000/api/v1
```

Generate signoff draft from latest evidence files:

```bash
make phase6-signoff-draft
make phase6-signoff-final
```

Check release-window readiness:

```bash
make phase6-window-status      # soft report
make phase6-window-gate        # strict gate (non-zero if not ready)
make phase6-window-gate-live   # strict + require non-local wave evidence
```

Run full local release simulation (pack + evidence + live waves + signoff + strict gate):

```bash
make phase6-local-sim
```

Build final release handoff package (bundle + manifest + tar.gz):

```bash
make phase6-handoff-pack
```
