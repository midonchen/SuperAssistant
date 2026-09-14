# Release Window Readiness Report

- Generated at (UTC): `2026-04-01T05:03:18Z`
- Strict mode: `True`
- Require non-local wave evidence: `False`

## Core Evidence

- Phase6 evidence file: `PHASE6_RELEASE_EVIDENCE_20260401_044442.md`
- Phase6 gate status: `PASS`
- Signoff draft file: `RELEASE_SIGNOFF_DRAFT_20260401_050318.md`

## Wave Readiness

- Wave 10%: file=`GRAY_WAVE_10_20260401_050307.md`, mode=`live`, snapshot=`OK`, base_url=`http://127.0.0.1:8000/api/v1`, non_local=`False`, ready=`True`
- Wave 50%: file=`GRAY_WAVE_50_20260401_050313.md`, mode=`live`, snapshot=`OK`, base_url=`http://127.0.0.1:8000/api/v1`, non_local=`False`, ready=`True`
- Wave 100%: file=`GRAY_WAVE_100_20260401_050317.md`, mode=`live`, snapshot=`OK`, base_url=`http://127.0.0.1:8000/api/v1`, non_local=`False`, ready=`True`

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