#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${SIM_PORT:-18080}"
BASE_URL="http://127.0.0.1:${PORT}/api/v1"
LOG_FILE="/tmp/superassistant_phase6_local_sim_api.log"

echo "[phase6-local-sim] 1/6 start local api on ${BASE_URL}..."
(
  cd services/api
  uvicorn main:app --host 127.0.0.1 --port "$PORT" >"$LOG_FILE" 2>&1
) &
API_PID=$!
trap 'kill "$API_PID" >/dev/null 2>&1 || true' EXIT
sleep 2

echo "[phase6-local-sim] 2/6 run release pack gate..."
bash scripts/run_phase6_release_pack.sh

echo "[phase6-local-sim] 3/6 generate phase6 evidence..."
bash scripts/generate_phase6_release_evidence.sh

echo "[phase6-local-sim] 4/6 record live wave checkpoints (10/50/100)..."
API_BASE_URL="$BASE_URL" python3 scripts/record_gray_wave_checkpoint.py --wave 10 --mode live --channel staging --note "local-simulation"
API_BASE_URL="$BASE_URL" python3 scripts/record_gray_wave_checkpoint.py --wave 50 --mode live --channel staging --note "local-simulation"
API_BASE_URL="$BASE_URL" python3 scripts/record_gray_wave_checkpoint.py --wave 100 --mode live --channel staging --note "local-simulation"

echo "[phase6-local-sim] 5/6 generate signoff draft..."
python3 scripts/generate_release_signoff_draft.py

echo "[phase6-local-sim] 6/6 strict release-window gate..."
python3 scripts/check_release_window_readiness.py --strict

echo "[phase6-local-sim] PASS"
