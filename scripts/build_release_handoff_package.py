#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "docs" / "release"
EVIDENCE_DIR = RELEASE_DIR / "evidence"
HANDOFF_DIR = RELEASE_DIR / "handoff"

PHASE6_PATTERN = re.compile(r"^PHASE6_RELEASE_EVIDENCE_(\d{8}_\d{6})\.md$")
WAVE_PATTERN = re.compile(r"^GRAY_WAVE_(10|50|100)_(\d{8}_\d{6})\.md$")
SIGNOFF_PATTERN = re.compile(r"^RELEASE_SIGNOFF_DRAFT_(\d{8}_\d{6})\.md$")
SIGNOFF_FINAL_PATTERN = re.compile(r"^RELEASE_SIGNOFF_FINAL_(\d{8}_\d{6})\.md$")
WINDOW_STRICT_PATTERN = re.compile(r"^RELEASE_WINDOW_STATUS_strict_(\d{8}_\d{6}(?:_\d{6})?)\.md$")


@dataclass
class SelectedArtifacts:
    phase6_evidence: Path
    wave10: Path
    wave50: Path
    wave100: Path
    signoff_draft: Path
    signoff_final: Path | None
    window_strict: Path
    uat_checklist: Path
    signoff_template: Path
    gray_runbook: Path


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


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


def _extract_value(text: str, prefix: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
            if value.startswith("`") and value.endswith("`") and len(value) >= 2:
                value = value[1:-1]
            return value
    return "UNKNOWN"


def _must(path: Path | None, label: str) -> Path:
    if path is None:
        raise RuntimeError(f"missing required artifact: {label}")
    return path


def select_artifacts(require_window_ready: bool) -> SelectedArtifacts:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    files = [p for p in EVIDENCE_DIR.iterdir() if p.is_file()]

    phase6_evidence = _must(_pick_latest(files, PHASE6_PATTERN), "PHASE6_RELEASE_EVIDENCE")
    wave10 = _must(_pick_latest_wave(files, "10"), "GRAY_WAVE_10")
    wave50 = _must(_pick_latest_wave(files, "50"), "GRAY_WAVE_50")
    wave100 = _must(_pick_latest_wave(files, "100"), "GRAY_WAVE_100")
    signoff_draft = _must(_pick_latest(files, SIGNOFF_PATTERN), "RELEASE_SIGNOFF_DRAFT")
    signoff_final = _pick_latest(files, SIGNOFF_FINAL_PATTERN)
    window_strict = _must(_pick_latest(files, WINDOW_STRICT_PATTERN), "RELEASE_WINDOW_STATUS_strict")

    if require_window_ready:
        text = window_strict.read_text(encoding="utf-8")
        overall_ready = _extract_value(text, "- Overall ready:")
        exit_status = _extract_value(text, "- Exit status (strict aware):")
        if overall_ready.lower() != "true" or exit_status.upper() != "PASS":
            raise RuntimeError(
                f"strict window status is not ready (overall={overall_ready}, strict={exit_status}): {window_strict.name}"
            )

    uat_checklist = RELEASE_DIR / "UAT_EXECUTION_CHECKLIST.md"
    signoff_template = RELEASE_DIR / "RELEASE_SIGNOFF_TEMPLATE.md"
    gray_runbook = RELEASE_DIR / "GRAY_RELEASE_RUNBOOK.md"
    for p in [uat_checklist, signoff_template, gray_runbook]:
        if not p.exists():
            raise RuntimeError(f"missing required release document: {p.relative_to(ROOT)}")

    return SelectedArtifacts(
        phase6_evidence=phase6_evidence,
        wave10=wave10,
        wave50=wave50,
        wave100=wave100,
        signoff_draft=signoff_draft,
        signoff_final=signoff_final,
        window_strict=window_strict,
        uat_checklist=uat_checklist,
        signoff_template=signoff_template,
        gray_runbook=gray_runbook,
    )


def copy_artifacts(bundle_dir: Path, selected: SelectedArtifacts) -> list[Path]:
    files_to_copy = [
        selected.phase6_evidence,
        selected.wave10,
        selected.wave50,
        selected.wave100,
        selected.signoff_draft,
        selected.window_strict,
        selected.uat_checklist,
        selected.signoff_template,
        selected.gray_runbook,
    ]
    if selected.signoff_final is not None:
        files_to_copy.append(selected.signoff_final)
    copied: list[Path] = []
    for src in files_to_copy:
        dest = bundle_dir / src.name
        shutil.copy2(src, dest)
        copied.append(dest)
    return copied


def write_manifest(bundle_dir: Path, copied: list[Path], selected: SelectedArtifacts, tar_name: str) -> Path:
    manifest = bundle_dir / "MANIFEST.md"
    lines = [
        "# Release Handoff Manifest",
        "",
        f"- Generated at (UTC): `{now_utc_iso()}`",
        f"- Source strict gate: `{selected.window_strict.name}`",
        f"- Package archive: `{tar_name}`",
        "",
        "## Included Files",
        "",
    ]
    for p in copied:
        lines.append(f"- `{p.name}`")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def create_archive(bundle_dir: Path, archive_path: Path) -> None:
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(bundle_dir, arcname=bundle_dir.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build release handoff package from latest evidence files.")
    parser.add_argument("--allow-not-ready", action="store_true", help="Allow package generation even when strict window gate is not ready.")
    args = parser.parse_args()

    selected = select_artifacts(require_window_ready=not args.allow_not_ready)

    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    stamp = now_compact()
    bundle_name = f"RELEASE_HANDOFF_{stamp}"
    bundle_dir = HANDOFF_DIR / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=False)

    copied = copy_artifacts(bundle_dir, selected)
    archive_path = HANDOFF_DIR / f"{bundle_name}.tar.gz"
    manifest_path = write_manifest(bundle_dir, copied, selected, archive_path.name)
    create_archive(bundle_dir, archive_path)

    print(f"[phase6-handoff] bundle dir: {bundle_dir.relative_to(ROOT)}")
    print(f"[phase6-handoff] manifest: {manifest_path.relative_to(ROOT)}")
    print(f"[phase6-handoff] archive: {archive_path.relative_to(ROOT)}")
    print("[phase6-handoff] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
