#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "release" / "evidence"
WAVE_PATTERN = re.compile(r"^GRAY_WAVE_(10|50|100)_(\d{8}_\d{6})\.md$")


@dataclass
class GateRuleResult:
    rule: str
    passed: bool
    severity: str
    observed: str
    threshold: str


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


def _pick_latest_wave_file(wave: str) -> Path:
    candidates: list[tuple[str, Path]] = []
    for path in EVIDENCE_DIR.iterdir():
        if not path.is_file():
            continue
        matched = WAVE_PATTERN.match(path.name)
        if not matched or matched.group(1) != wave:
            continue
        candidates.append((matched.group(2), path))
    if not candidates:
        raise RuntimeError(f"no wave report found for wave={wave}")
    candidates.sort(key=lambda pair: pair[0])
    return candidates[-1][1]


def _extract_value(text: str, prefix: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith(prefix):
            continue
        value = line[len(prefix) :].strip()
        if value.startswith("`") and value.endswith("`") and len(value) >= 2:
            return value[1:-1]
        return value
    return "UNKNOWN"


def _extract_raw_snapshot_json(text: str) -> dict[str, Any] | None:
    matched = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not matched:
        return None
    return json.loads(matched.group(1))


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _build_rule(
    *,
    rule: str,
    observed: float | int | str,
    threshold: float | int | str,
    passed: bool,
    severity: str,
) -> GateRuleResult:
    return GateRuleResult(
        rule=rule,
        passed=passed,
        severity=severity,
        observed=str(observed),
        threshold=str(threshold),
    )


def evaluate_wave_report(
    *,
    report_text: str,
    max_pending_approvals: int,
    max_pending_audit_tasks: int,
    max_parser_failure_ratio: float,
    max_stt_failure_ratio: float,
    max_parser_fallback_ratio: float,
    max_stt_fallback_ratio: float,
    critical_parser_failure_ratio: float,
    critical_stt_failure_ratio: float,
    critical_parser_fallback_ratio: float,
    critical_stt_fallback_ratio: float,
    allow_quota_rejections: bool,
) -> tuple[str, list[GateRuleResult], dict[str, Any]]:
    mode = _extract_value(report_text, "- Mode:")
    snapshot_status = _extract_value(report_text, "- Snapshot status:")
    snapshot = _extract_raw_snapshot_json(report_text)
    rules: list[GateRuleResult] = []

    rules.append(
        _build_rule(
            rule="wave_mode_is_live",
            observed=mode,
            threshold="live",
            passed=mode.lower() == "live",
            severity="hold",
        )
    )

    snapshot_ok = snapshot_status.upper() == "OK"
    rules.append(
        _build_rule(
            rule="snapshot_status_ok",
            observed=snapshot_status,
            threshold="OK",
            passed=snapshot_ok,
            severity="rollback",
        )
    )

    if snapshot is None:
        rules.append(
            _build_rule(
                rule="raw_snapshot_json_present",
                observed="missing",
                threshold="present",
                passed=False,
                severity="rollback",
            )
        )
        return _decide(rules), rules, {}

    dashboard_data = ((snapshot.get("dashboard") or {}).get("data") or {}) if isinstance(snapshot, dict) else {}
    approvals_data = ((snapshot.get("approvals") or {}).get("data") or {}) if isinstance(snapshot, dict) else {}
    audit_data = ((snapshot.get("audit_tasks") or {}).get("data") or {}) if isinstance(snapshot, dict) else {}
    kpi = (dashboard_data.get("kpi") or {}) if isinstance(dashboard_data, dict) else {}
    ai_runtime = (dashboard_data.get("ai_runtime") or {}) if isinstance(dashboard_data, dict) else {}

    pending_approvals = int(_num(approvals_data.get("total", 0)))
    pending_audit_tasks = int(_num(audit_data.get("total", 0)))
    stt_breaker_open = _as_bool(ai_runtime.get("stt_breaker_open", False))
    parser_breaker_open = _as_bool(ai_runtime.get("parser_breaker_open", False))

    voice_requests = _num(ai_runtime.get("voice_requests", 0))
    ocr_requests = _num(ai_runtime.get("ocr_requests", 0))
    parse_requests = voice_requests + ocr_requests
    stt_external_calls = _num(ai_runtime.get("stt_external_calls", 0))
    parser_external_calls = _num(ai_runtime.get("parser_external_calls", 0))
    stt_external_failures = _num(ai_runtime.get("stt_external_failures", 0))
    parser_external_failures = _num(ai_runtime.get("parser_external_failures", 0))
    stt_fallbacks = _num(ai_runtime.get("stt_fallbacks", 0))
    parser_fallbacks = _num(ai_runtime.get("parser_fallbacks", 0))
    stt_quota_rejections = _num(ai_runtime.get("stt_quota_rejections", 0))
    parser_quota_rejections = _num(ai_runtime.get("parser_quota_rejections", 0))
    quota_rejections = stt_quota_rejections + parser_quota_rejections

    stt_failure_ratio = _safe_ratio(stt_external_failures, stt_external_calls)
    parser_failure_ratio = _safe_ratio(parser_external_failures, parser_external_calls)
    stt_fallback_ratio = _safe_ratio(stt_fallbacks, voice_requests)
    parser_fallback_ratio = _safe_ratio(parser_fallbacks, parse_requests)

    rules.append(
        _build_rule(
            rule="pending_approvals_within_limit",
            observed=pending_approvals,
            threshold=f"<={max_pending_approvals}",
            passed=pending_approvals <= max_pending_approvals,
            severity="hold",
        )
    )
    rules.append(
        _build_rule(
            rule="pending_audit_tasks_within_limit",
            observed=pending_audit_tasks,
            threshold=f"<={max_pending_audit_tasks}",
            passed=pending_audit_tasks <= max_pending_audit_tasks,
            severity="hold",
        )
    )
    rules.append(
        _build_rule(
            rule="stt_breaker_not_open",
            observed=stt_breaker_open,
            threshold="False",
            passed=not stt_breaker_open,
            severity="rollback",
        )
    )
    rules.append(
        _build_rule(
            rule="parser_breaker_not_open",
            observed=parser_breaker_open,
            threshold="False",
            passed=not parser_breaker_open,
            severity="rollback",
        )
    )
    rules.append(
        _build_rule(
            rule="stt_failure_ratio_within_limit",
            observed=f"{stt_failure_ratio:.4f}",
            threshold=f"<={max_stt_failure_ratio:.4f}",
            passed=stt_failure_ratio <= max_stt_failure_ratio,
            severity="hold",
        )
    )
    rules.append(
        _build_rule(
            rule="parser_failure_ratio_within_limit",
            observed=f"{parser_failure_ratio:.4f}",
            threshold=f"<={max_parser_failure_ratio:.4f}",
            passed=parser_failure_ratio <= max_parser_failure_ratio,
            severity="hold",
        )
    )
    rules.append(
        _build_rule(
            rule="stt_fallback_ratio_within_limit",
            observed=f"{stt_fallback_ratio:.4f}",
            threshold=f"<={max_stt_fallback_ratio:.4f}",
            passed=stt_fallback_ratio <= max_stt_fallback_ratio,
            severity="hold",
        )
    )
    rules.append(
        _build_rule(
            rule="parser_fallback_ratio_within_limit",
            observed=f"{parser_fallback_ratio:.4f}",
            threshold=f"<={max_parser_fallback_ratio:.4f}",
            passed=parser_fallback_ratio <= max_parser_fallback_ratio,
            severity="hold",
        )
    )
    rules.append(
        _build_rule(
            rule="quota_rejections_allowed",
            observed=int(quota_rejections),
            threshold="0 (or allow_quota_rejections=true)",
            passed=allow_quota_rejections or quota_rejections <= 0,
            severity="hold",
        )
    )
    rules.append(
        _build_rule(
            rule="stt_failure_ratio_not_critical",
            observed=f"{stt_failure_ratio:.4f}",
            threshold=f"<{critical_stt_failure_ratio:.4f}",
            passed=stt_failure_ratio < critical_stt_failure_ratio,
            severity="rollback",
        )
    )
    rules.append(
        _build_rule(
            rule="parser_failure_ratio_not_critical",
            observed=f"{parser_failure_ratio:.4f}",
            threshold=f"<{critical_parser_failure_ratio:.4f}",
            passed=parser_failure_ratio < critical_parser_failure_ratio,
            severity="rollback",
        )
    )
    rules.append(
        _build_rule(
            rule="stt_fallback_ratio_not_critical",
            observed=f"{stt_fallback_ratio:.4f}",
            threshold=f"<{critical_stt_fallback_ratio:.4f}",
            passed=stt_fallback_ratio < critical_stt_fallback_ratio,
            severity="rollback",
        )
    )
    rules.append(
        _build_rule(
            rule="parser_fallback_ratio_not_critical",
            observed=f"{parser_fallback_ratio:.4f}",
            threshold=f"<{critical_parser_fallback_ratio:.4f}",
            passed=parser_fallback_ratio < critical_parser_fallback_ratio,
            severity="rollback",
        )
    )

    metrics = {
        "total_users": int(_num(kpi.get("total_users", 0))),
        "pending_approvals": pending_approvals,
        "pending_audit_tasks": pending_audit_tasks,
        "voice_requests": int(voice_requests),
        "ocr_requests": int(ocr_requests),
        "stt_external_calls": int(stt_external_calls),
        "parser_external_calls": int(parser_external_calls),
        "stt_failure_ratio": stt_failure_ratio,
        "parser_failure_ratio": parser_failure_ratio,
        "stt_fallback_ratio": stt_fallback_ratio,
        "parser_fallback_ratio": parser_fallback_ratio,
        "quota_rejections": int(quota_rejections),
        "stt_breaker_open": stt_breaker_open,
        "parser_breaker_open": parser_breaker_open,
    }
    return _decide(rules), rules, metrics


def _decide(rules: list[GateRuleResult]) -> str:
    if any((not rule.passed) and rule.severity == "rollback" for rule in rules):
        return "ROLLBACK"
    if any(not rule.passed for rule in rules):
        return "HOLD"
    return "CONTINUE"


def build_markdown_report(
    *,
    wave: str,
    source_file: Path,
    decision: str,
    rules: list[GateRuleResult],
    metrics: dict[str, Any],
) -> str:
    lines: list[str] = []
    lines.append("# Gray Wave Gate Evaluation")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{now_utc_iso()}`")
    lines.append(f"- Wave: `{wave}%`")
    lines.append(f"- Source wave report: `{source_file.name}`")
    lines.append(f"- Auto decision: `{decision}`")
    lines.append("")
    lines.append("## Rule Checks")
    lines.append("")
    for rule in rules:
        status = "PASS" if rule.passed else "FAIL"
        lines.append(
            f"- `{rule.rule}`: `{status}` | severity=`{rule.severity}` | observed=`{rule.observed}` | threshold=`{rule.threshold}`"
        )
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    if metrics:
        for key, value in metrics.items():
            if isinstance(value, float):
                lines.append(f"- {key}: `{value:.4f}`")
            else:
                lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- `n/a`")
    lines.append("")
    lines.append("## Next Action")
    lines.append("")
    if decision == "CONTINUE":
        lines.append("- Promote to next wave.")
    elif decision == "HOLD":
        lines.append("- Keep current wave and investigate failing non-critical rules.")
    else:
        lines.append("- Trigger rollback process and stop rollout progression.")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate gray-wave snapshot and output gate decision.")
    parser.add_argument("--wave", required=True, choices=["10", "50", "100"])
    parser.add_argument("--wave-report", default="", help="Optional explicit wave report path")
    parser.add_argument("--require-continue", action="store_true", help="Exit non-zero unless decision is CONTINUE")
    parser.add_argument("--max-pending-approvals", type=int, default=20)
    parser.add_argument("--max-pending-audit-tasks", type=int, default=50)
    parser.add_argument("--max-parser-failure-ratio", type=float, default=0.20)
    parser.add_argument("--max-stt-failure-ratio", type=float, default=0.20)
    parser.add_argument("--max-parser-fallback-ratio", type=float, default=0.30)
    parser.add_argument("--max-stt-fallback-ratio", type=float, default=0.30)
    parser.add_argument("--critical-parser-failure-ratio", type=float, default=0.50)
    parser.add_argument("--critical-stt-failure-ratio", type=float, default=0.50)
    parser.add_argument("--critical-parser-fallback-ratio", type=float, default=0.80)
    parser.add_argument("--critical-stt-fallback-ratio", type=float, default=0.80)
    parser.add_argument("--allow-quota-rejections", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    report_path = Path(args.wave_report).resolve() if args.wave_report else _pick_latest_wave_file(args.wave)
    if not report_path.exists():
        raise RuntimeError(f"wave report not found: {report_path}")

    report_text = report_path.read_text(encoding="utf-8")
    decision, rules, metrics = evaluate_wave_report(
        report_text=report_text,
        max_pending_approvals=args.max_pending_approvals,
        max_pending_audit_tasks=args.max_pending_audit_tasks,
        max_parser_failure_ratio=args.max_parser_failure_ratio,
        max_stt_failure_ratio=args.max_stt_failure_ratio,
        max_parser_fallback_ratio=args.max_parser_fallback_ratio,
        max_stt_fallback_ratio=args.max_stt_fallback_ratio,
        critical_parser_failure_ratio=args.critical_parser_failure_ratio,
        critical_stt_failure_ratio=args.critical_stt_failure_ratio,
        critical_parser_fallback_ratio=args.critical_parser_fallback_ratio,
        critical_stt_fallback_ratio=args.critical_stt_fallback_ratio,
        allow_quota_rejections=args.allow_quota_rejections,
    )

    out_path = EVIDENCE_DIR / f"GRAY_WAVE_GATE_{args.wave}_{now_compact()}.md"
    out_text = build_markdown_report(
        wave=args.wave,
        source_file=report_path,
        decision=decision,
        rules=rules,
        metrics=metrics,
    )
    out_path.write_text(out_text, encoding="utf-8")

    print(f"[phase6-wave-gate] report generated: {out_path.relative_to(ROOT)}")
    print(f"[phase6-wave-gate] decision={decision}")
    if args.require_continue and decision != "CONTINUE":
        print("[phase6-wave-gate] FAIL (require-continue enabled)")
        return 1
    print("[phase6-wave-gate] PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[phase6-wave-gate] ERROR: {exc}")
        raise
