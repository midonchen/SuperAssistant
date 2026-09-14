#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

EVIDENCE_DIR="docs/release/evidence"
mkdir -p "$EVIDENCE_DIR"

TS_UTC="$(date -u +"%Y%m%d_%H%M%S")"
NOW_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
REPORT_PATH="$EVIDENCE_DIR/PHASE6_RELEASE_EVIDENCE_${TS_UTC}.md"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_REV="$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"
else
  GIT_REV="N/A (no git repository)"
fi

cat >"$REPORT_PATH" <<EOF
# Phase 6 Release Evidence Report

- Generated at (UTC): \`$NOW_UTC\`
- Host: \`$(uname -a)\`
- Python: \`$(python3 --version 2>/dev/null || echo "unavailable")\`
- Git revision: \`$GIT_REV\`

## Command Results

EOF

OVERALL_OK=1

run_and_capture() {
  local title="$1"
  local cmd="$2"
  local started ended status
  local output_file

  started="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  output_file="$(mktemp)"
  if bash -lc "$cmd" >"$output_file" 2>&1; then
    status="PASS"
  else
    status="FAIL"
    OVERALL_OK=0
  fi
  ended="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

  {
    echo "### $title"
    echo
    echo "- Command: \`$cmd\`"
    echo "- Started (UTC): \`$started\`"
    echo "- Ended (UTC): \`$ended\`"
    echo "- Status: \`$status\`"
    echo
    echo '```text'
    cat "$output_file"
    echo '```'
    echo
  } >>"$REPORT_PATH"

  rm -f "$output_file"
}

run_and_capture "Release Pack Gate" "make phase6-pack"

if [[ $OVERALL_OK -eq 1 ]]; then
  SUMMARY_STATUS="PASS"
else
  SUMMARY_STATUS="FAIL"
fi

{
  echo "## Summary"
  echo
  echo "- Final status: \`$SUMMARY_STATUS\`"
  echo "- Release signoff template: \`docs/release/RELEASE_SIGNOFF_TEMPLATE.md\`"
  echo "- UAT checklist: \`docs/release/UAT_EXECUTION_CHECKLIST.md\`"
  echo "- Gray runbook: \`docs/release/GRAY_RELEASE_RUNBOOK.md\`"
} >>"$REPORT_PATH"

echo "[phase6-evidence] report generated: $REPORT_PATH"

if [[ $OVERALL_OK -eq 1 ]]; then
  echo "[phase6-evidence] PASS"
  exit 0
fi

echo "[phase6-evidence] FAIL"
exit 1
