#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "release" / "evidence"

PHASE6_PATTERN = re.compile(r"^PHASE6_RELEASE_EVIDENCE_(\d{8}_\d{6})\.md$")
SIGNOFF_DRAFT_PATTERN = re.compile(r"^RELEASE_SIGNOFF_DRAFT_(\d{8}_\d{6})\.md$")
WINDOW_STRICT_PATTERN = re.compile(r"^RELEASE_WINDOW_STATUS_strict_(\d{8}_\d{6}(?:_\d{6})?)\.md$")
WAVE_PATTERN = re.compile(r"^GRAY_WAVE_(10|50|100)_(\d{8}_\d{6})\.md$")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _pick_latest(paths: list[Path], pattern: re.Pattern[str]) -> Path | None:
    matches: list[tuple[str, Path]] = []
    for path in paths:
        m = pattern.match(path.name)
        if not m:
            continue
        matches.append((m.group(1), path))
    if not matches:
        return None
    matches.sort(key=lambda x: x[0])
    return matches[-1][1]


def _pick_latest_wave(paths: list[Path], wave: str) -> Path | None:
    matches: list[tuple[str, Path]] = []
    for path in paths:
        m = WAVE_PATTERN.match(path.name)
        if not m:
            continue
        if m.group(1) != wave:
            continue
        matches.append((m.group(2), path))
    if not matches:
        return None
    matches.sort(key=lambda x: x[0])
    return matches[-1][1]


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


def _require(path: Path | None, name: str) -> Path:
    if path is None:
        raise RuntimeError(f"missing required artifact: {name}")
    return path


def _validate_window_ready(window_status_file: Path) -> None:
    text = window_status_file.read_text(encoding="utf-8")
    overall = _extract_value(text, "- Overall ready:")
    strict = _extract_value(text, "- Exit status (strict aware):")
    if overall.lower() != "true" or strict.upper() != "PASS":
        raise RuntimeError(
            f"strict window gate is not ready (overall={overall}, strict={strict}): {window_status_file.name}"
        )


def build_signoff_markdown(
    *,
    release_id: str,
    target_date: str,
    api_revision: str,
    mobile_build: str,
    decision: str,
    notes: str,
    selected: dict[str, Path],
) -> str:
    decision = decision.upper()
    if decision not in {"GO", "NO-GO"}:
        raise ValueError("decision must be GO or NO-GO")

    lines: list[str] = []
    lines.append("# Release Signoff Final")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{now_utc_iso()}`")
    lines.append("")
    lines.append("## Release Metadata")
    lines.append("")
    lines.append(f"- Release ID: `{release_id}`")
    lines.append(f"- Target date: `{target_date}`")
    lines.append(f"- API revision: `{api_revision}`")
    lines.append(f"- Mobile build: `{mobile_build}`")
    lines.append("- Scope: `MVP iOS + API + Core Admin`")
    lines.append("")
    lines.append("## Evidence")
    lines.append("")
    lines.append(f"- Phase6 evidence: `{selected['phase6'].name}`")
    lines.append(f"- Strict window status: `{selected['window_strict'].name}`")
    lines.append(f"- Signoff draft: `{selected['draft'].name}`")
    lines.append(f"- Wave 10: `{selected['wave10'].name}`")
    lines.append(f"- Wave 50: `{selected['wave50'].name}`")
    lines.append(f"- Wave 100: `{selected['wave100'].name}`")
    lines.append("")
    lines.append("## Signoff Matrix")
    lines.append("")
    lines.append("1. Product owner: `[ ] Approve  [ ] Reject`")
    lines.append("2. Engineering owner: `[ ] Approve  [ ] Reject`")
    lines.append("3. QA/UAT owner: `[ ] Approve  [ ] Reject`")
    lines.append("4. Operations/Release owner: `[ ] Approve  [ ] Reject`")
    lines.append("")
    lines.append("## Final Decision")
    lines.append("")
    if decision == "GO":
        lines.append("- `[x] GO`")
        lines.append("- `[ ] NO-GO`")
    else:
        lines.append("- `[ ] GO`")
        lines.append("- `[x] NO-GO`")
    lines.append(f"- Decision timestamp (UTC): `{now_utc_iso()}`")
    lines.append(f"- Notes: `{notes}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate final release signoff document from latest artifacts.")
    parser.add_argument("--release-id", default="REL-MVP")
    parser.add_argument("--target-date", default="TBD")
    parser.add_argument("--api-revision", default="1.1")
    parser.add_argument("--mobile-build", default="TBD")
    parser.add_argument("--decision", default="GO", help="GO or NO-GO")
    parser.add_argument("--notes", default="Pending owner signatures")
    args = parser.parse_args()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    files = [p for p in EVIDENCE_DIR.iterdir() if p.is_file()]

    selected = {
        "phase6": _require(_pick_latest(files, PHASE6_PATTERN), "PHASE6_RELEASE_EVIDENCE"),
        "draft": _require(_pick_latest(files, SIGNOFF_DRAFT_PATTERN), "RELEASE_SIGNOFF_DRAFT"),
        "window_strict": _require(_pick_latest(files, WINDOW_STRICT_PATTERN), "RELEASE_WINDOW_STATUS_strict"),
        "wave10": _require(_pick_latest_wave(files, "10"), "GRAY_WAVE_10"),
        "wave50": _require(_pick_latest_wave(files, "50"), "GRAY_WAVE_50"),
        "wave100": _require(_pick_latest_wave(files, "100"), "GRAY_WAVE_100"),
    }

    _validate_window_ready(selected["window_strict"])

    out_path = EVIDENCE_DIR / f"RELEASE_SIGNOFF_FINAL_{now_compact()}.md"
    out_text = build_signoff_markdown(
        release_id=args.release_id,
        target_date=args.target_date,
        api_revision=args.api_revision,
        mobile_build=args.mobile_build,
        decision=args.decision,
        notes=args.notes,
        selected=selected,
    )
    out_path.write_text(out_text, encoding="utf-8")
    print(f"[phase6-signoff-final] generated: {out_path.relative_to(ROOT)}")
    print("[phase6-signoff-final] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
