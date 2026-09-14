#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "${1:-}" == "" ]]; then
  echo "Usage: bash scripts/run_gray_wave_execution.sh <10|50|100> [--finalize]"
  exit 1
fi

WAVE="$1"
FINALIZE_FLAG="${2:-}"
API_BASE_URL="${API_BASE_URL:-http://localhost:8000/api/v1}"
RELEASE_CHANNEL="${RELEASE_CHANNEL:-staging}"
RELEASE_NOTE="${RELEASE_NOTE:-wave-execution}"
REQUIRE_NON_LOCAL_WAVES="${REQUIRE_NON_LOCAL_WAVES:-0}"

case "$WAVE" in
  10) REQUIRED_WAVES="10" ;;
  50) REQUIRED_WAVES="10,50" ;;
  100) REQUIRED_WAVES="10,50,100" ;;
  *)
    echo "[phase6-wave-exec] invalid wave: $WAVE"
    exit 1
    ;;
esac

echo "[phase6-wave-exec] 1/5 record live wave checkpoint (wave=${WAVE}%)..."
API_BASE_URL="$API_BASE_URL" RELEASE_CHANNEL="$RELEASE_CHANNEL" \
  python3 scripts/record_gray_wave_checkpoint.py \
    --wave "$WAVE" \
    --mode live \
    --channel "$RELEASE_CHANNEL" \
    --note "$RELEASE_NOTE"

echo "[phase6-wave-exec] 2/5 evaluate wave gate decision (must be CONTINUE)..."
python3 scripts/evaluate_gray_wave_gate.py --wave "$WAVE" --require-continue

echo "[phase6-wave-exec] 3/5 refresh signoff draft..."
python3 scripts/generate_release_signoff_draft.py

WINDOW_ARGS=(--required-waves "$REQUIRED_WAVES" --strict)
if [[ "$REQUIRE_NON_LOCAL_WAVES" == "1" ]]; then
  WINDOW_ARGS+=(--require-non-local-wave-evidence)
fi
echo "[phase6-wave-exec] 4/5 strict readiness gate for waves: ${REQUIRED_WAVES} (non-local=${REQUIRE_NON_LOCAL_WAVES})..."
python3 scripts/check_release_window_readiness.py "${WINDOW_ARGS[@]}"

if [[ "$WAVE" == "100" || "$FINALIZE_FLAG" == "--finalize" ]]; then
  echo "[phase6-wave-exec] 5/5 finalize signoff and build handoff package..."
  python3 scripts/finalize_release_signoff.py
  python3 scripts/build_release_handoff_package.py
else
  echo "[phase6-wave-exec] 5/5 finalize step skipped (wave < 100 and no --finalize)."
fi

echo "[phase6-wave-exec] PASS"
