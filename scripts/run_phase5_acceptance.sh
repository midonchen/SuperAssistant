#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[phase5] running governance checks..."
npm run check:all

echo "[phase5] running key auth/offline/admin acceptance tests..."
python3 -m pytest -q services/api/tests/test_auth_inventory_admin.py -k "login_and_inventory_flow or token_refresh_rotation_and_logout_flow or logout_cannot_revoke_other_users_session or offline_replay_queue_flow or push_preference_and_jobs"

echo "[phase5] acceptance passed."
