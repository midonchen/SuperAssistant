#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "release" / "evidence"

PHASE6_PATTERN = re.compile(r"^PHASE6_RELEASE_EVIDENCE_(\d{8}_\d{6})\.md$")
WAVE_PATTERN = re.compile(r"^GRAY_WAVE_(10|50|100)_(\d{8}_\d{6})\.md$")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def pick_latest(paths: list[Path], pattern: re.Pattern[str]) -> Path | None:
    candidates: list[tuple[str, Path]] = []
    for p in paths:
        m = pattern.match(p.name)
        if not m:
            continue
        candidates.append((m.group(1), p))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]


def pick_latest_wave(paths: list[Path], wave: str) -> Path | None:
    candidates: list[tuple[str, Path]] = []
    for p in paths:
        m = WAVE_PATTERN.match(p.name)
        if not m:
            continue
        if m.group(1) != wave:
            continue
        candidates.append((m.group(2), p))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]


def read_status_line(path: Path, prefix: str) -> str:
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith(prefix):
                value = line.replace(prefix, "").strip()
                if value.startswith("`") and value.endswith("`") and len(value) >= 2:
                    value = value[1:-1]
                return value
    except Exception:
        return "unknown"
    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate release signoff draft from latest evidence files.")
    parser.add_argument("--release-id", default=os.getenv("RELEASE_ID", "REL-MVP"))
    parser.add_argument("--target-date", default=os.getenv("RELEASE_TARGET_DATE", "TBD"))
    parser.add_argument("--api-revision", default=os.getenv("RELEASE_API_REVISION", "1.1"))
    parser.add_argument("--mobile-build", default=os.getenv("RELEASE_MOBILE_BUILD", "TBD"))
    args = parser.parse_args()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    files = [p for p in EVIDENCE_DIR.iterdir() if p.is_file()]

    latest_phase6 = pick_latest(files, PHASE6_PATTERN)
    wave10 = pick_latest_wave(files, "10")
    wave50 = pick_latest_wave(files, "50")
    wave100 = pick_latest_wave(files, "100")

    release_gate_status = "UNKNOWN"
    if latest_phase6 is not None:
        release_gate_status = read_status_line(latest_phase6, "- Final status:")

    report_path = EVIDENCE_DIR / f"RELEASE_SIGNOFF_DRAFT_{now_compact()}.md"
    lines: list[str] = []
    lines.append("# Release Signoff Draft")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{now_utc_iso()}`")
    lines.append(f"- Release ID: `{args.release_id}`")
    lines.append(f"- Target date: `{args.target_date}`")
    lines.append(f"- API revision: `{args.api_revision}`")
    lines.append(f"- Mobile build: `{args.mobile_build}`")
    lines.append("")
    lines.append("## Evidence Index")
    lines.append("")
    lines.append(f"- Latest phase6 evidence: `{latest_phase6.name if latest_phase6 else 'MISSING'}`")
    lines.append(f"- Phase6 gate status: `{release_gate_status}`")
    lines.append(f"- Wave 10 record: `{wave10.name if wave10 else 'MISSING'}`")
    lines.append(f"- Wave 50 record: `{wave50.name if wave50 else 'MISSING'}`")
    lines.append(f"- Wave 100 record: `{wave100.name if wave100 else 'MISSING'}`")
    lines.append("")
    lines.append("## Required Evidence Checklist")
    lines.append("")
    lines.append(f"- [ ] `make phase6-ready` + `make phase6-load` via phase6 evidence (`{latest_phase6.name if latest_phase6 else 'MISSING'}`)")
    lines.append("- [ ] UAT checklist completed (`docs/release/UAT_EXECUTION_CHECKLIST.md`)")
    lines.append("- [ ] Gray runbook acknowledged (`docs/release/GRAY_RELEASE_RUNBOOK.md`)")
    lines.append(f"- [ ] Wave 10 log exists (`{wave10.name if wave10 else 'MISSING'}`)")
    lines.append(f"- [ ] Wave 50 log exists (`{wave50.name if wave50 else 'MISSING'}`)")
    lines.append(f"- [ ] Wave 100 log exists (`{wave100.name if wave100 else 'MISSING'}`)")
    lines.append("")
    lines.append("## Risk Notes")
    lines.append("")
    lines.append("- Open critical risks: `________________`")
    lines.append("- Mitigations in place: `________________`")
    lines.append("- Rollback owner and ETA: `________________`")
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
    lines.append("- `[ ] GO`")
    lines.append("- `[ ] NO-GO`")
    lines.append("- Decision timestamp: `________________`")
    lines.append("- Notes: `________________`")
    lines.append("")
    lines.append("## Next Step")
    lines.append("")
    lines.append("- Copy approved decisions into `docs/release/RELEASE_SIGNOFF_TEMPLATE.md`.")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[phase6-signoff] draft generated: {report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
