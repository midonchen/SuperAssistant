# Phase 6 UAT Execution Checklist

## Scope Baseline

- Product baseline: `SuperAssistant_PRD_v1.1.md`
- API baseline: `交付物01_API字段级JSON示例附录_v1.1.md`
- UI baseline: `交付物02_UI线框清单附录_v1.1.md`
- MVP scope: iOS + API + Core Admin (Dashboard / Users / Audit)

## Environment

- Staging API URL: `________________`
- App build version: `________________`
- Test window (start/end): `________________`
- Test owner: `________________`

## UAT Scenarios

1. Voice parse + confirm
   - Target: parse response <= 1.5s (P95 <= 1200ms baseline)
   - Evidence: `________________`
   - Result: `[ ] PASS  [ ] FAIL`
2. OCR parse + manual fill
   - Target: single-ticket parse <= 3s (P95 <= 2800ms baseline)
   - Evidence: `________________`
   - Result: `[ ] PASS  [ ] FAIL`
3. Auto decay safety
   - Target: no negative inventory after scheduled decay
   - Evidence: `________________`
   - Result: `[ ] PASS  [ ] FAIL`
4. Purchase suggestion formula
   - Target: safety margin aligns to 20% rule
   - Evidence: `________________`
   - Result: `[ ] PASS  [ ] FAIL`
5. Auth/session governance
   - Target: silent refresh success/failure branches correct; max-session eviction traceable
   - Evidence: `________________`
   - Result: `[ ] PASS  [ ] FAIL`
6. Offline replay + conflict
   - Target: offline queue replay succeeds; `BIZ_409_CONFLICT` recovery works
   - Evidence: `________________`
   - Result: `[ ] PASS  [ ] FAIL`
7. Admin governance
   - Target: revoke request requires approval; audit review and security events complete
   - Evidence: `________________`
   - Result: `[ ] PASS  [ ] FAIL`
8. Performance baseline gates
   - Target: `make phase6-ready` and `make phase6-load` both PASS
   - Evidence: `________________`
   - Result: `[ ] PASS  [ ] FAIL`

## Defect Summary

- Critical: `____`
- High: `____`
- Medium/Low: `____`
- Blockers for release: `________________`

## UAT Decision

- `[ ] Approve for gray release`
- `[ ] Reject and re-test required`
- Decision owner / date: `________________`
