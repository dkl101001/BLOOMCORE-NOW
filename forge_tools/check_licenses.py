# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Deterministically verify the repository's file-level license membrane."""

from __future__ import annotations

import json
import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "build"}
TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".yml",
    ".yaml",
    ".toml",
    ".json",
    ".html",
    ".css",
    ".js",
}
SPECIAL_TEXT = {".gitignore"}

PATH_RULES = (
    ("releases/2026-W42-reconstruction-preflight/src/", "MPL-2.0"),
    ("releases/2026-W42-reconstruction-preflight/tests/", "MPL-2.0"),
    ("releases/2026-W42-reconstruction-preflight/experiment.py", "MPL-2.0"),
    ("EDP-02/runner/", "MPL-2.0"),
    ("EDP-02/analysis/", "MPL-2.0"),
    ("EDP-02/tests/", "MPL-2.0"),
    ("EDP-01/runner/", "MPL-2.0"),
    ("EDP-01/analysis/", "MPL-2.0"),
    ("EDP-01/tests/", "MPL-2.0"),
    ("forge_tools/", "MPL-2.0"),
    ("shared/deterministic-tools/", "MPL-2.0"),
    ("shared/runtime-contracts/", "AGPL-3.0-only"),
    ("releases/2026-W31-bloomcore-receipt/apps/receipt-server/", "AGPL-3.0-only"),
    ("releases/2026-W31-bloomcore-receipt/packages/evidence-validator/", "MPL-2.0"),
    ("releases/2026-W31-bloomcore-receipt/packages/receipt-schema/", "Apache-2.0"),
    ("releases/2026-W31-bloomcore-receipt/examples/", "Apache-2.0"),
    ("releases/2026-W35-panic-professionally/apps/dashboard/", "AGPL-3.0-only"),
    (
        "releases/2026-W35-panic-professionally/packages/panic_professionally/dashboard.",
        "AGPL-3.0-only",
    ),
    ("releases/2026-W35-panic-professionally/packages/panic_professionally/", "MPL-2.0"),
    ("releases/2026-W35-panic-professionally/tests/", "MPL-2.0"),
    ("releases/2026-W35-panic-professionally/examples/", "Apache-2.0"),
    ("releases/2026-W35-panic-professionally/contracts/", "Apache-2.0"),
    ("releases/2026-W35-panic-professionally/docs/", "Apache-2.0"),
    ("releases/2026-W36-triad-workflow/packages/triad_workflow/", "MPL-2.0"),
    ("releases/2026-W36-triad-workflow/tests/", "MPL-2.0"),
    ("releases/2026-W36-triad-workflow/contracts/", "Apache-2.0"),
    ("releases/2026-W36-triad-workflow/docs/", "Apache-2.0"),
    ("releases/2026-W36-triad-workflow/examples/", "Apache-2.0"),
    ("releases/2026-W36-triad-workflow/templates/", "Apache-2.0"),
    ("releases/2026-W36-triad-workflow/evidence/", "Apache-2.0"),
)


def expected_license(relative: str) -> str | None:
    if relative.startswith(("EDP-01/", "EDP-02/")) and relative.endswith(".md"):
        return "Apache-2.0"
    for prefix, license_id in PATH_RULES:
        if relative.startswith(prefix):
            return license_id
    return None


def iter_text_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        component_source = ROOT / "releases/flock-off/source"
        if path.is_relative_to(component_source) and any(part in {"work", ".venv"} or part.endswith(".egg-info") for part in path.relative_to(component_source).parts):
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if "LICENSES" in path.parts or path.name in {"NOTICE"}:
            continue
        if path.suffix in TEXT_SUFFIXES or path.name in SPECIAL_TEXT:
            files.append(path)
    return sorted(files)


def declared_license(path: pathlib.Path, source: str) -> str | None:
    """Recognize already-declared JSON SPDX metadata without mutating receipts.

    Ordinary text must keep its existing SPDX header. JSON uses a structured
    root-level field because JSON comments are not legal and a generated
    receipt's canonical bytes cannot be changed by adding a fake header.
    """
    if path.suffix == ".json":
        try:
            payload = json.loads(source)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        declared = payload.get("spdx_license_identifier")
        if isinstance(declared, str):
            return declared if declared in {"Apache-2.0", "MPL-2.0", "AGPL-3.0-only"} else None
        marker = "SPDX-License-Identifier: "
        for key in ("$comment", "_license"):
            value = payload.get(key)
            if isinstance(value, str) and value.startswith(marker):
                found = value[len(marker):].strip()
                return found if found in {"Apache-2.0", "MPL-2.0", "AGPL-3.0-only"} else None
        return None
    marker = "SPDX-License-Identifier: "
    for line in source[:600].splitlines():
        if marker in line:
            return line.split(marker, 1)[1].split(" ", 1)[0].strip()
    return None


def main() -> int:
    failures: list[str] = []
    component = ROOT / "releases/flock-off"
    source_root = component / "source"
    license_map = json.loads((component / "SOURCE_LICENSES.json").read_text(encoding="utf-8"))
    mapped = license_map["files"]
    if hashlib.sha256((source_root / "LICENSE").read_bytes()).hexdigest() != "8efd18c6e6527d9f853673c691ebbc0fc017b7a549c26b834f93bb0645b7093e":
        failures.append("FLOCK OFF: pinned combined AGPL-3.0-only license changed")
    for relative, record in mapped.items():
        candidate = (source_root / relative).resolve()
        if not candidate.is_relative_to(source_root.resolve()) or not candidate.is_file():
            failures.append(f"FLOCK OFF: invalid mapped source path {relative}")
        elif not isinstance(record.get("spdx_license_identifier"), str) or not record["spdx_license_identifier"] or hashlib.sha256(candidate.read_bytes()).hexdigest() != record["sha256"]:
            failures.append(f"FLOCK OFF: source license mapping mismatch {relative}")
    for path in iter_text_files():
        relative = path.relative_to(ROOT).as_posix()
        if path.is_relative_to(source_root) and path.relative_to(source_root).as_posix() in mapped:
            continue
        text = path.read_text(encoding="utf-8")
        declared = declared_license(path, text)
        if not declared:
            failures.append(f"{relative}: missing or invalid SPDX identifier")
            continue
        required = expected_license(relative)
        if required and declared != required:
            failures.append(f"{relative}: expected {required}; observed {declared}")

    required_texts = {
        "Apache-2.0": ROOT / "LICENSES" / "Apache-2.0.txt",
        "MPL-2.0": ROOT / "LICENSES" / "MPL-2.0.txt",
        "AGPL-3.0-only": ROOT / "LICENSES" / "AGPL-3.0-only.txt",
    }
    for license_id, path in required_texts.items():
        if not path.is_file() or path.stat().st_size < 5_000:
            failures.append(f"{license_id}: full license text missing or unexpectedly short")

    if failures:
        print("LICENSE CHECK FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"LICENSE CHECK PASSED ({len(iter_text_files())} text files inspected)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
