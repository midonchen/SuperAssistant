#!/usr/bin/env bash
set -euo pipefail

# Enforce presence of architecture review artifact for tracked architecture changes.
if [[ ! -f docs/architecture/ARCH_REVIEW_LOG.md ]]; then
  echo "architecture-review-check: missing docs/architecture/ARCH_REVIEW_LOG.md"
  exit 1
fi

echo "architecture-review-check: passed"
