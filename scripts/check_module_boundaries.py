#!/usr/bin/env python3
"""Simple module-boundary check for services/api/src/modules.

Rules:
- module code can import:
  - itself (`modules.<name>.*`)
  - `core.*`
  - external packages
- direct imports from other modules are blocked
  unless listed in ALLOWED_CROSS_MODULE_IMPORTS.
"""

from __future__ import annotations

import ast
import pathlib
import sys
from typing import Dict, List, Set

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODULES_ROOT = ROOT / "services" / "api" / "src" / "modules"

ALLOWED_CROSS_MODULE_IMPORTS: Dict[str, Set[str]] = {
    # Example: "admin": {"auth", "inventory"}
    "admin": {"auth", "inventory"},
}


def detect_module(file_path: pathlib.Path) -> str | None:
    parts = file_path.parts
    if "modules" not in parts:
        return None
    idx = parts.index("modules")
    if idx + 1 < len(parts):
        return parts[idx + 1]
    return None


def parse_imports(file_path: pathlib.Path) -> List[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    imports: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def target_module(import_stmt: str) -> str | None:
    if not import_stmt.startswith("modules."):
        return None
    chunks = import_stmt.split(".")
    return chunks[1] if len(chunks) > 1 else None


def main() -> int:
    violations: List[str] = []
    for py_file in MODULES_ROOT.rglob("*.py"):
        owner = detect_module(py_file)
        if owner is None:
            continue
        for imp in parse_imports(py_file):
            target = target_module(imp)
            if target is None or target == owner:
                continue
            allowed_targets = ALLOWED_CROSS_MODULE_IMPORTS.get(owner, set())
            if target not in allowed_targets:
                violations.append(
                    f"module-boundary-check: {py_file} imports modules.{target} (owner={owner})"
                )

    if violations:
        print("\n".join(violations))
        return 1

    print("module-boundary-check: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
