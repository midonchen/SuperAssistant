#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS_DOC = ROOT / "docs" / "roadmap" / "IMPLEMENTATION_STATUS.md"
ROADMAP_DOC = ROOT / "docs" / "roadmap" / "MVP_10_WEEK_EXECUTION.md"
EVIDENCE_DIR = ROOT / "docs" / "release" / "evidence"
REPORT_DIR = ROOT / "docs" / "roadmap" / "status"

PHASE_PART_PATTERN = re.compile(r"^- Phase\s+(\d+)\b.*\(part\s+(\d+)\):", re.IGNORECASE)
STRICT_WINDOW_PATTERN = re.compile(r"^RELEASE_WINDOW_STATUS_strict_(\d{8}_\d{6}(?:_\d{6})?)\.md$")
WAVE_PATTERN = re.compile(r"^GRAY_WAVE_(10|50|100)_(\d{8}_\d{6})\.md$")


@dataclass
class PhasePart:
    phase: int
    part: int
    line: str


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _extract_section_bullets(markdown: str, heading: str) -> list[str]:
    lines = markdown.splitlines()
    in_section = False
    bullets: list[str] = []
    for line in lines:
        if line.strip() == heading:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.strip().startswith("- "):
            bullets.append(line.strip()[2:].strip())
    return bullets


def _extract_phase_parts(markdown: str) -> list[PhasePart]:
    parts: list[PhasePart] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        match = PHASE_PART_PATTERN.match(line)
        if not match:
            continue
        parts.append(PhasePart(phase=int(match.group(1)), part=int(match.group(2)), line=line))
    return parts


def _read_text(path: Path) -> str:
    if not path.exists():
        raise RuntimeError(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def _extract_roadmap_rows(markdown: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line.startswith("| W"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if not re.match(r"^W\d", cells[0]):
            continue
        rows.append((cells[0], cells[1], cells[2]))
    return rows


def _pick_latest(paths: list[Path], pattern: re.Pattern[str]) -> Path | None:
    matched: list[tuple[str, Path]] = []
    for path in paths:
        m = pattern.match(path.name)
        if not m:
            continue
        matched.append((m.group(1), path))
    if not matched:
        return None
    matched.sort(key=lambda pair: pair[0])
    return matched[-1][1]


def _pick_latest_wave(paths: list[Path], wave: str) -> Path | None:
    matched: list[tuple[str, Path]] = []
    for path in paths:
        m = WAVE_PATTERN.match(path.name)
        if not m:
            continue
        if m.group(1) != wave:
            continue
        matched.append((m.group(2), path))
    if not matched:
        return None
    matched.sort(key=lambda pair: pair[0])
    return matched[-1][1]


def _extract_line_value(text: str, prefix: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith(prefix):
            continue
        value = line[len(prefix) :].strip()
        if value.startswith("`") and value.endswith("`") and len(value) >= 2:
            return value[1:-1]
        return value
    return "UNKNOWN"


def _is_non_local_base_url(wave_text: str) -> bool:
    base = _extract_line_value(wave_text, "- API Base URL:")
    base_l = base.lower()
    return not any(
        token in base_l
        for token in ("localhost", "127.0.0.1", "0.0.0.0", "http://[::1]", "https://[::1]")
    )


def build_report() -> tuple[str, dict[str, int | str]]:
    status_text = _read_text(STATUS_DOC)
    roadmap_text = _read_text(ROADMAP_DOC)
    evidence_files = [path for path in EVIDENCE_DIR.glob("*") if path.is_file()] if EVIDENCE_DIR.exists() else []

    phase_parts = _extract_phase_parts(status_text)
    current_phase = max((p.phase for p in phase_parts), default=0)
    max_part = max((p.part for p in phase_parts), default=0)
    completed_phase_count = len({p.phase for p in phase_parts})
    roadmap_rows = _extract_roadmap_rows(roadmap_text)
    total_phase_count = len(roadmap_rows)

    not_implemented = _extract_section_bullets(status_text, "## Not Yet Implemented (next iterations)")

    latest_strict = _pick_latest(evidence_files, STRICT_WINDOW_PATTERN)
    strict_ready = False
    if latest_strict:
        strict_text = latest_strict.read_text(encoding="utf-8")
        strict_status = _extract_line_value(strict_text, "- Exit status (strict aware):")
        strict_ready = strict_status.upper() == "PASS"

    wave_10 = _pick_latest_wave(evidence_files, "10")
    wave_50 = _pick_latest_wave(evidence_files, "50")
    wave_100 = _pick_latest_wave(evidence_files, "100")
    has_all_waves = wave_10 is not None and wave_50 is not None and wave_100 is not None

    has_non_local_wave = False
    for wave_file in (wave_10, wave_50, wave_100):
        if wave_file is None:
            continue
        if _is_non_local_base_url(wave_file.read_text(encoding="utf-8")):
            has_non_local_wave = True
            break

    pending_items = list(not_implemented)
    if has_all_waves and not has_non_local_wave:
        pending_items.append("Wave evidence currently appears local-only; staging/prod live execution evidence is still missing.")
    if latest_strict is None:
        pending_items.append("Strict release-window status evidence is missing.")
    elif not strict_ready:
        pending_items.append("Latest strict release-window gate is not PASS.")

    lines: list[str] = []
    lines.append("# Phase Progress Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{now_utc_iso()}`")
    lines.append(f"- Current phase: `Phase {current_phase}`")
    lines.append(f"- Completed phases in roadmap: `{completed_phase_count}/{total_phase_count}`")
    lines.append(f"- Completed plan increments (part): `{max_part}`")
    lines.append("")
    lines.append("## Phase Map")
    lines.append("")
    for week, phase, deliverables in roadmap_rows:
        phase_match = re.search(r"Phase\s+(\d+)", phase, flags=re.IGNORECASE)
        phase_num = int(phase_match.group(1)) if phase_match else 999
        marker = "DONE" if phase_num <= current_phase else "PENDING"
        lines.append(f"- {week} | {phase} | {marker} | {deliverables}")
    lines.append("")
    lines.append("## Release Evidence Snapshot")
    lines.append("")
    lines.append(f"- Latest strict window report: `{latest_strict.name if latest_strict else 'MISSING'}`")
    lines.append(f"- Strict window ready: `{strict_ready}`")
    lines.append(f"- Latest wave 10 report: `{wave_10.name if wave_10 else 'MISSING'}`")
    lines.append(f"- Latest wave 50 report: `{wave_50.name if wave_50 else 'MISSING'}`")
    lines.append(f"- Latest wave 100 report: `{wave_100.name if wave_100 else 'MISSING'}`")
    lines.append(f"- Non-local wave evidence detected: `{has_non_local_wave}`")
    lines.append("")
    lines.append("## Remaining Work")
    lines.append("")
    if pending_items:
        for item in pending_items:
            lines.append(f"- {item}")
    else:
        lines.append("- No remaining work is listed in the status baseline.")
    lines.append("")

    summary = {
        "current_phase": current_phase,
        "max_part": max_part,
        "pending_count": len(pending_items),
    }
    return "\n".join(lines) + "\n", summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate current phase progress and remaining-work report.")
    parser.add_argument("--stdout", action="store_true", help="Print report to stdout in addition to file output.")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_text, summary = build_report()
    out_path = REPORT_DIR / f"PHASE_STATUS_REPORT_{now_compact()}.md"
    out_path.write_text(report_text, encoding="utf-8")

    print(f"[phase-status] report generated: {out_path.relative_to(ROOT)}")
    print(
        "[phase-status] "
        f"phase=Phase {summary['current_phase']}, part={summary['max_part']}, pending={summary['pending_count']}"
    )
    if args.stdout:
        print("\n" + report_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
