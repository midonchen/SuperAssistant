# Gray Release Runbook

## Goal

Execute staged rollout with measurable gates and deterministic rollback.

## Rollout Plan

1. Wave 1: 10% internal/beta users
2. Wave 2: 50% users
3. Wave 3: 100% users

Advance only when each wave satisfies monitoring and incident criteria.

Wave checkpoint recording command:

1. Template before wave starts:
   - `make phase6-wave-template WAVE=10`
2. Live snapshot during wave:
   - `make phase6-wave-live WAVE=10 API_BASE_URL=http://localhost:8000/api/v1`
   - Evaluate auto gate decision:
     - `make phase6-wave-gate WAVE=10`
     - strict mode (must be `CONTINUE`): `make phase6-wave-gate WAVE=10 STRICT=1`
   - Or one-command wave execution:
     - `make phase6-wave-exec WAVE=10 API_BASE_URL=http://localhost:8000/api/v1`
     - `make phase6-wave-exec-final WAVE=100 API_BASE_URL=http://localhost:8000/api/v1`
3. Generated logs:
   - `docs/release/evidence/GRAY_WAVE_<wave>_<timestamp>.md`
   - `docs/release/evidence/GRAY_WAVE_GATE_<wave>_<timestamp>.md`
4. Window readiness check:
   - `make phase6-window-status` (soft)
   - `make phase6-window-gate` (strict, must pass before final signoff)
   - `make phase6-window-gate-live` (strict + require non-local wave evidence for staging/prod)
5. Optional local dry-run:
   - `make phase6-local-sim`
6. Build release handoff package:
   - `make phase6-handoff-pack`

## Pre-Release Gates

1. `make phase6-pack` passes.
2. UAT checklist completed:
   - `docs/release/UAT_EXECUTION_CHECKLIST.md`
3. Release signoff prepared:
   - `docs/release/RELEASE_SIGNOFF_TEMPLATE.md`

## Live Monitoring (Must Watch)

- API error rate (`SYS_5xx`, `AI_504_TIMEOUT`)
- AI parse timeout/fallback ratio
- Offline replay failure ratio
- Push delivery success rate
- iOS crash-free session rate
- DB pool saturation and job backlog

## Wave Gate Criteria

1. Blocker incidents: `0`
2. Critical regressions: `0`
3. Error-rate increase vs baseline: `< 30%`
4. Core flow success (login, parse, confirm, inventory write): `>= 99%`
5. Auto wave gate decision must be `CONTINUE` (if `HOLD`/`ROLLBACK`, stop promotion)
6. For staging/prod release, non-local wave evidence gate must pass (`make phase6-window-gate-live`)

## Rollback Strategy

1. Server rollback
   - Roll back API deployment to previous stable revision.
2. Feature degradation
   - Disable external AI parse path via runtime config, keep manual flow available.
3. Session protection
   - If auth regression occurs, revoke affected sessions and require re-login.

Rollback decision owner: `________________`

## Release Communication

1. Start notification (wave entry)
2. Mid-wave status every 30 minutes
3. Wave complete or rollback announcement

Communication owner: `________________`
