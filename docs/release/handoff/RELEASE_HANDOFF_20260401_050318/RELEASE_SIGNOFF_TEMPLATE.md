# Release Signoff Template

## Release Metadata

- Release ID: `________________`
- Target date: `________________`
- API revision: `________________`
- Mobile build: `________________`
- Scope: `MVP iOS + API + Core Admin`

## Required Evidence

1. Governance + regression gate: `make phase6-ready` result
2. External-load benchmark: `make phase6-load` result
3. UAT checklist:
   - `docs/release/UAT_EXECUTION_CHECKLIST.md`
4. Gray release runbook acknowledgement:
   - `docs/release/GRAY_RELEASE_RUNBOOK.md`
5. Wave execution logs:
   - `docs/release/evidence/GRAY_WAVE_*.md`
6. Wave gate evaluation logs:
   - `docs/release/evidence/GRAY_WAVE_GATE_*.md`
7. Signoff draft (auto-compiled):
   - `docs/release/evidence/RELEASE_SIGNOFF_DRAFT_*.md`
8. Signoff final (gate-validated):
   - `docs/release/evidence/RELEASE_SIGNOFF_FINAL_*.md`
9. Non-local wave evidence gate for staging/prod:
   - `make phase6-window-gate-live` result

## Risk Assessment

- Open critical risks: `________________`
- Mitigations in place: `________________`
- Rollback owner and ETA: `________________`

## Signoff Matrix

1. Product owner
   - Name: `________________`
   - Decision: `[ ] Approve  [ ] Reject`
   - Date: `________________`
2. Engineering owner
   - Name: `________________`
   - Decision: `[ ] Approve  [ ] Reject`
   - Date: `________________`
3. QA/UAT owner
   - Name: `________________`
   - Decision: `[ ] Approve  [ ] Reject`
   - Date: `________________`
4. Operations/Release owner
   - Name: `________________`
   - Decision: `[ ] Approve  [ ] Reject`
   - Date: `________________`

## Final Decision

- `[ ] GO`
- `[ ] NO-GO`
- Decision timestamp: `________________`
- Notes: `________________`
