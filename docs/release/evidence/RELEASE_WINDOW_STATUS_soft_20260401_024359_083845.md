# Release Window Readiness Report

- Generated at (UTC): `2026-04-01T02:43:59Z`
- Strict mode: `False`

## Core Evidence

- Phase6 evidence file: `PHASE6_RELEASE_EVIDENCE_20260401_015037.md`
- Phase6 gate status: `PASS`
- Signoff draft file: `RELEASE_SIGNOFF_DRAFT_20260401_020617.md`

## Wave Readiness

- Wave 10%: file=`GRAY_WAVE_10_20260401_015648.md`, mode=`live`, snapshot=`OK`, ready=`True`
- Wave 50%: file=`MISSING`, mode=`MISSING`, snapshot=`MISSING`, ready=`False`
- Wave 100%: file=`MISSING`, mode=`MISSING`, snapshot=`MISSING`, ready=`False`

## Summary

- Phase6 gates ready: `True`
- Required waves ready: `False`
- Signoff draft ready: `True`
- Overall ready: `False`
- Exit status (strict aware): `PASS`

## Action

- If a wave is not ready, run:
  - `make phase6-wave-live WAVE=<10|50|100> API_BASE_URL=...`
- Regenerate signoff draft after new evidence:
  - `make phase6-signoff-draft`