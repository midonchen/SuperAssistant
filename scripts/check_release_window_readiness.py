#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "release" / "evidence"

PHASE6_PATTERN = re.compile(r"^PHASE6_RELEASE_EVIDENCE_(\d{8}_\d{6})\.md$")
SIGNOFF_PATTERN = re.compile(r"^RELEASE_SIGNOFF_DRAFT_(\d{8}_\d{6})\.md$")
WAVE_PATTERN = re.compile(r"^GRAY_WAVE_(10|50|100)_(\d{8}_\d{6})\.md$")


@dataclass
class WaveStatus:
    wave: str
    file_name: str
    mode: str
    snapshot_status: str
    api_base_url: str
    non_local_base: bool
    ready: bool


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


def _extract_line_value(text: str, prefix: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
            if value.startswith("`") and value.endswith("`") and len(value) >= 2:
                return value[1:-1]
            return value
    return "UNKNOWN"


def _pick_latest(paths: list[Path], pattern: re.Pattern[str]) -> Path | None:
    matched: list[tuple[str, Path]] = []
    for p in paths:
        m = pattern.match(p.name)
        if not m:
            continue
        matched.append((m.group(1), p))
    if not matched:
        return None
    matched.sort(key=lambda x: x[0])
    return matched[-1][1]


def _pick_latest_wave(paths: list[Path], wave: str) -> Path | None:
    matched: list[tuple[str, Path]] = []
    for p in paths:
        m = WAVE_PATTERN.match(p.name)
        if not m:
            continue
        if m.group(1) != wave:
            continue
        matched.append((m.group(2), p))
    if not matched:
        return None
    matched.sort(key=lambda x: x[0])
    return matched[-1][1]


def _is_non_local_base_url(base_url: str) -> bool:
    lowered = base_url.strip().lower()
    if lowered in {"", "unknown"}:
        return False
    local_markers = ("localhost", "127.0.0.1", "0.0.0.0", "[::1]")
    return not any(marker in lowered for marker in local_markers)


def _wave_status(paths: list[Path], wave: str) -> WaveStatus:
    latest = _pick_latest_wave(paths, wave)
    if latest is None:
        return WaveStatus(
            wave=wave,
            file_name="MISSING",
            mode="MISSING",
            snapshot_status="MISSING",
            api_base_url="MISSING",
            non_local_base=False,
            ready=False,
        )
    text = latest.read_text(encoding="utf-8")
    mode = _extract_line_value(text, "- Mode:")
    snapshot_status = _extract_line_value(text, "- Snapshot status:")
    api_base_url = _extract_line_value(text, "- API Base URL:")
    non_local_base = _is_non_local_base_url(api_base_url)
    ready = mode.lower() == "live" and snapshot_status.upper() == "OK"
    return WaveStatus(
        wave=wave,
        file_name=latest.name,
        mode=mode,
        snapshot_status=snapshot_status,
        api_base_url=api_base_url,
        non_local_base=non_local_base,
        ready=ready,
    )


def build_report(required_waves: list[str], strict: bool, require_non_local_wave_evidence: bool) -> tuple[str, bool]:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    files = [p for p in EVIDENCE_DIR.iterdir() if p.is_file()]

    latest_phase6 = _pick_latest(files, PHASE6_PATTERN)
    latest_signoff = _pick_latest(files, SIGNOFF_PATTERN)

    phase6_status = "MISSING"
    phase6_ready = False
    if latest_phase6 is not None:
        text = latest_phase6.read_text(encoding="utf-8")
        phase6_status = _extract_line_value(text, "- Final status:")
        phase6_ready = phase6_status.upper() == "PASS"

    waves = [_wave_status(files, wave) for wave in required_waves]
    waves_ready = all(w.ready for w in waves)
    non_local_waves_ready = all(w.non_local_base for w in waves)
    signoff_ready = latest_signoff is not None

    non_local_gate_ready = non_local_waves_ready if require_non_local_wave_evidence else True
    overall_ready = phase6_ready and waves_ready and signoff_ready and non_local_gate_ready
    strict_result = overall_ready if strict else True

    lines: list[str] = []
    lines.append("# Release Window Readiness Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{now_utc_iso()}`")
    lines.append(f"- Strict mode: `{strict}`")
    lines.append(f"- Require non-local wave evidence: `{require_non_local_wave_evidence}`")
    lines.append("")
    lines.append("## Core Evidence")
    lines.append("")
    lines.append(f"- Phase6 evidence file: `{latest_phase6.name if latest_phase6 else 'MISSING'}`")
    lines.append(f"- Phase6 gate status: `{phase6_status}`")
    lines.append(f"- Signoff draft file: `{latest_signoff.name if latest_signoff else 'MISSING'}`")
    lines.append("")
    lines.append("## Wave Readiness")
    lines.append("")
    for wave in waves:
        lines.append(
            f"- Wave {wave.wave}%: file=`{wave.file_name}`, mode=`{wave.mode}`, snapshot=`{wave.snapshot_status}`, "
            f"base_url=`{wave.api_base_url}`, non_local=`{wave.non_local_base}`, ready=`{wave.ready}`"
        )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Phase6 gates ready: `{phase6_ready}`")
    lines.append(f"- Required waves ready: `{waves_ready}`")
    lines.append(f"- Non-local wave evidence ready: `{non_local_gate_ready}`")
    lines.append(f"- Signoff draft ready: `{signoff_ready}`")
    lines.append(f"- Overall ready: `{overall_ready}`")
    lines.append(f"- Exit status (strict aware): `{'PASS' if strict_result else 'FAIL'}`")
    lines.append("")
    lines.append("## Action")
    lines.append("")
    lines.append("- If a wave is not ready, run:")
    lines.append("  - `make phase6-wave-live WAVE=<10|50|100> API_BASE_URL=...`")
    lines.append("- If non-local evidence is required, use staging/prod API_BASE_URL instead of localhost.")
    lines.append("- Regenerate signoff draft after new evidence:")
    lines.append("  - `make phase6-signoff-draft`")

    return "\n".join(lines), strict_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Check release-window readiness based on evidence artifacts.")
    parser.add_argument("--required-waves", default="10,50,100", help="Comma-separated waves, e.g. 10,50,100")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when not fully ready.")
    parser.add_argument(
        "--require-non-local-wave-evidence",
        action="store_true",
        help="Require all selected wave records to use non-local API base URL (staging/prod).",
    )
    args = parser.parse_args()

    required_waves = [w.strip() for w in args.required_waves.split(",") if w.strip()]
    for wave in required_waves:
        if wave not in {"10", "50", "100"}:
            raise ValueError(f"invalid wave: {wave}")

    report, pass_result = build_report(
        required_waves,
        strict=args.strict,
        require_non_local_wave_evidence=args.require_non_local_wave_evidence,
    )
    mode_label = "strict" if args.strict else "soft"
    out_path = EVIDENCE_DIR / f"RELEASE_WINDOW_STATUS_{mode_label}_{now_compact()}.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"[phase6-window] report generated: {out_path.relative_to(ROOT)}")
    print(f"[phase6-window] {'PASS' if pass_result else 'FAIL'}")
    return 0 if pass_result else 1


if __name__ == "__main__":
    sys.exit(main())
