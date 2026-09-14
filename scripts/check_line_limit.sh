#!/usr/bin/env bash
set -euo pipefail

MAX_LINES=800
EXIT_CODE=0

# Handwritten source patterns.
PATTERNS=("*.py" "*.ts" "*.tsx" "*.js" "*.jsx" "*.dart" "*.sh")
EXCLUDES=(
  "*/node_modules/*"
  "*/.next/*"
  "*/build/*"
  "*/generated/*"
  "*/.venv/*"
  "*/venv/*"
  "*.g.dart"
  "*.pb.*"
)

match_excluded() {
  local path="$1"
  for ex in "${EXCLUDES[@]}"; do
    if [[ "$path" == $ex ]]; then
      return 0
    fi
  done
  return 1
}

while IFS= read -r file; do
  match_excluded "$file" && continue
  lines=$(wc -l < "$file" | tr -d ' ')
  if (( lines > MAX_LINES )); then
    echo "line-limit-check: $file has $lines lines (> $MAX_LINES)"
    EXIT_CODE=1
  fi
done < <(find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.dart" -o -name "*.sh" \))

exit $EXIT_CODE
