#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "release" / "evidence"
NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def request_json(
    *,
    base_url: str,
    path: str,
    method: str = "GET",
    token: str | None = None,
    write: bool = False,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    full_url = f"{base_url.rstrip('/')}{path}"
    payload = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(full_url, data=payload, method=method.upper())
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Request-Id", f"wave-{utc_compact()}")
    req.add_header("X-App-Version", "1.1.0")
    req.add_header("X-Platform", "ios")
    if write:
        req.add_header("Idempotency-Key", f"wave-op-{utc_compact()}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with NO_PROXY_OPENER.open(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise RuntimeError(f"invalid json response shape from {path}")
            return data
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed: HTTP {exc.code} {body_text}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {path} failed: {exc}") from exc


def safe_get(d: dict[str, Any], *path: str, default: Any = None) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def collect_live_snapshot(base_url: str, admin_phone: str, admin_code: str, device_id: str) -> dict[str, Any]:
    login_resp = request_json(
        base_url=base_url,
        path="/auth/sms/login",
        method="POST",
        write=True,
        body={"phone": admin_phone, "code": admin_code, "device_id": device_id},
    )
    token = safe_get(login_resp, "data", "access_token", default="")
    if not token:
        raise RuntimeError("login succeeded but missing access_token")

    dashboard = request_json(
        base_url=base_url,
        path="/admin/dashboard/summary",
        method="GET",
        token=token,
    )
    approvals = request_json(
        base_url=base_url,
        path="/admin/approvals?status=PENDING",
        method="GET",
        token=token,
    )
    audit_tasks = request_json(
        base_url=base_url,
        path="/admin/audit/tasks",
        method="GET",
        token=token,
    )

    return {
        "dashboard": dashboard,
        "approvals": approvals,
        "audit_tasks": audit_tasks,
    }


def build_report(
    *,
    wave: str,
    channel: str,
    operator: str,
    mode: str,
    base_url: str,
    note: str,
    snapshot: dict[str, Any] | None,
    snapshot_error: str | None,
) -> str:
    now = utc_now_iso()
    lines: list[str] = []
    lines.append("# Gray Wave Execution Record")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{now}`")
    lines.append(f"- Wave: `{wave}%`")
    lines.append(f"- Channel: `{channel}`")
    lines.append(f"- Operator: `{operator}`")
    lines.append(f"- Mode: `{mode}`")
    lines.append(f"- API Base URL: `{base_url}`")
    if note:
        lines.append(f"- Note: `{note}`")
    lines.append(f"- Host: `{platform.platform()}`")
    lines.append("")

    lines.append("## Gate Status")
    lines.append("")
    lines.append("- `make phase6-ready`: `[ ] PASS  [ ] FAIL`")
    lines.append("- `make phase6-load`: `[ ] PASS  [ ] FAIL`")
    lines.append("- Current wave decision: `[ ] CONTINUE  [ ] HOLD  [ ] ROLLBACK`")
    lines.append("")

    lines.append("## Live Snapshot")
    lines.append("")
    if snapshot_error:
        lines.append(f"- Snapshot status: `FAILED`")
        lines.append(f"- Error: `{snapshot_error}`")
        lines.append("")
    elif snapshot is None:
        lines.append("- Snapshot status: `SKIPPED (template mode)`")
        lines.append("")
    else:
        dashboard = snapshot.get("dashboard", {})
        approvals = snapshot.get("approvals", {})
        audit_tasks = snapshot.get("audit_tasks", {})
        kpi = safe_get(dashboard, "data", "kpi", default={}) or {}
        ai_runtime = safe_get(dashboard, "data", "ai_runtime", default={}) or {}
        pending_approvals = safe_get(approvals, "data", "total", default=0)
        pending_audits = safe_get(audit_tasks, "data", "total", default=0)
        lines.append("- Snapshot status: `OK`")
        lines.append("- Key metrics:")
        lines.append(f"  - total_users: `{kpi.get('total_users', 'n/a')}`")
        lines.append(f"  - pending_audit_tasks(kpi): `{kpi.get('pending_audit_tasks', 'n/a')}`")
        lines.append(f"  - push_failed: `{kpi.get('push_failed', 'n/a')}`")
        lines.append(f"  - pending_approvals: `{pending_approvals}`")
        lines.append(f"  - pending_audit_tasks(list): `{pending_audits}`")
        lines.append(f"  - parser_fallbacks: `{ai_runtime.get('parser_fallbacks', 'n/a')}`")
        lines.append(f"  - stt_fallbacks: `{ai_runtime.get('stt_fallbacks', 'n/a')}`")
        lines.append(f"  - parser_quota_rejections: `{ai_runtime.get('parser_quota_rejections', 'n/a')}`")
        lines.append(f"  - stt_quota_rejections: `{ai_runtime.get('stt_quota_rejections', 'n/a')}`")
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>Raw Snapshot JSON</summary>")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(snapshot, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("## Incidents")
    lines.append("")
    lines.append("- New incidents in this wave: `________________`")
    lines.append("- Critical regressions: `________________`")
    lines.append("- Rollback trigger matched: `[ ] YES  [ ] NO`")
    lines.append("")

    lines.append("## Next Action")
    lines.append("")
    lines.append("- `[ ] Promote to next wave`")
    lines.append("- `[ ] Keep current wave`")
    lines.append("- `[ ] Roll back`")
    lines.append("- Action owner/date: `________________`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record gray release wave checkpoint.")
    parser.add_argument("--wave", required=True, choices=["10", "50", "100"], help="Wave percentage.")
    parser.add_argument("--channel", default=os.getenv("RELEASE_CHANNEL", "staging"), help="Release channel.")
    parser.add_argument("--mode", choices=["template", "live"], default="template", help="template=generate placeholders, live=collect API snapshot")
    parser.add_argument("--base-url", default=os.getenv("API_BASE_URL", "http://localhost:8000/api/v1"), help="API base url")
    parser.add_argument("--admin-phone", default=os.getenv("SUPERASSISTANT_ADMIN_PHONE", "13900139000"))
    parser.add_argument("--admin-code", default=os.getenv("SUPERASSISTANT_ADMIN_CODE", "123456"))
    parser.add_argument("--device-id", default=os.getenv("WAVE_DEVICE_ID", "ops-wave-recorder"))
    parser.add_argument("--operator", default=os.getenv("RELEASE_OPERATOR", os.getenv("USER", "unknown")))
    parser.add_argument("--note", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = utc_compact()
    report_path = EVIDENCE_DIR / f"GRAY_WAVE_{args.wave}_{timestamp}.md"

    snapshot: dict[str, Any] | None = None
    snapshot_error: str | None = None
    if args.mode == "live":
        try:
            snapshot = collect_live_snapshot(
                base_url=args.base_url,
                admin_phone=args.admin_phone,
                admin_code=args.admin_code,
                device_id=args.device_id,
            )
        except Exception as exc:
            snapshot_error = str(exc)

    report = build_report(
        wave=args.wave,
        channel=args.channel,
        operator=args.operator,
        mode=args.mode,
        base_url=args.base_url,
        note=args.note,
        snapshot=snapshot,
        snapshot_error=snapshot_error,
    )
    report_path.write_text(report, encoding="utf-8")

    print(f"[phase6-wave] report generated: {report_path.relative_to(ROOT)}")
    if snapshot_error:
        print(f"[phase6-wave] live snapshot failed: {snapshot_error}")
        return 1
    print("[phase6-wave] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
