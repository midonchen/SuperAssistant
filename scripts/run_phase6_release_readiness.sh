#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[phase6-ready] 1/4 governance checks..."
npm run check:all

echo "[phase6-ready] 2/4 api regression..."
python3 -m pytest -q services/api/tests

echo "[phase6-ready] 3/4 phase5 acceptance..."
bash scripts/run_phase5_acceptance.sh

echo "[phase6-ready] 4/4 phase6 perf smoke..."
python3 scripts/run_phase6_perf_smoke.py

echo "[phase6-ready] PASS"
