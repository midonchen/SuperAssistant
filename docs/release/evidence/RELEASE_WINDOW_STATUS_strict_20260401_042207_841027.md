# Release Window Readiness Report

- Generated at (UTC): `2026-04-01T04:22:07Z`
- Strict mode: `True`
- Require non-local wave evidence: `False`

## Core Evidence

- Phase6 evidence file: `PHASE6_RELEASE_EVIDENCE_20260401_024637.md`
- Phase6 gate status: `PASS`
- Signoff draft file: `RELEASE_SIGNOFF_DRAFT_20260401_030608.md`

## Wave Readiness

- Wave 10%: file=`GRAY_WAVE_10_20260401_030608.md`, mode=`live`, snapshot=`OK`, base_url=`http://127.0.0.1:18080/api/v1`, non_local=`False`, ready=`True`
- Wave 50%: file=`GRAY_WAVE_50_20260401_024650.md`, mode=`live`, snapshot=`OK`, base_url=`http://127.0.0.1:18080/api/v1`, non_local=`False`, ready=`True`
- Wave 100%: file=`GRAY_WAVE_100_20260401_030608.md`, mode=`live`, snapshot=`OK`, base_url=`http://127.0.0.1:18080/api/v1`, non_local=`False`, ready=`True`

## Summary

- Phase6 gates ready: `True`
- Required waves ready: `True`
- Non-local wave evidence ready: `True`
- Signoff draft ready: `True`
- Overall ready: `True`
- Exit status (strict aware): `PASS`

## Action

- If a wave is not ready, run:
  - `make phase6-wave-live WAVE=<10|50|100> API_BASE_URL=...`
- If non-local evidence is required, use staging/prod API_BASE_URL instead of localhost.
- Regenerate signoff draft after new evidence:
  - `make phase6-signoff-draft`