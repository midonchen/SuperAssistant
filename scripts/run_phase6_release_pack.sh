#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REQUIRED_DOCS=(
  "docs/release/UAT_EXECUTION_CHECKLIST.md"
  "docs/release/GRAY_RELEASE_RUNBOOK.md"
  "docs/release/RELEASE_SIGNOFF_TEMPLATE.md"
)

echo "[phase6-pack] 1/3 verify release artifacts..."
for path in "${REQUIRED_DOCS[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "[phase6-pack] missing required artifact: $path"
    exit 1
  fi
done

echo "[phase6-pack] 2/3 execute release-readiness gate..."
bash scripts/run_phase6_release_readiness.sh

echo "[phase6-pack] 3/3 execute external-load gate..."
python3 scripts/run_phase6_external_load.py

echo "[phase6-pack] PASS"
echo "[phase6-pack] Next: complete docs/release/RELEASE_SIGNOFF_TEMPLATE.md and attach UAT/gray evidence."
