# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Verify mandatory custody and weekly public-boundary declarations."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED_ROOT = {
    "README.md",
    "LICENSE.md",
    "CUSTODY.md",
    "DISCLAIMER.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "RELEASE_INDEX.md",
    "BUILD_QUEUE.md",
}
REQUIRED_ROOT_BOUNDARY_KEYS = {
    "public_safe: true",
    "private_logic_exposed: false",
    "tests_included: true",
    "docs_updated: true",
    "license_compatible: true",
    "phase36_37_custody_present: true",
    "authorship_preserved: true",
}
REQUIRED_RELEASE_BOUNDARY_KEYS = {
    "public_safe: true",
    "private_logic_exposed: false",
    "tests_included: true",
    "docs_updated: true",
    "license_compatible: true",
    "authorship_preserved: true",
}
PROTECTED_PATH_MARKERS = {
    "private_eca",
    "private-orchestration",
    "substrate_memory_private",
    "production_secrets",
}


def main() -> int:
    failures: list[str] = []

    for name in sorted(REQUIRED_ROOT):
        if not (ROOT / name).is_file():
            failures.append(f"missing root custody file: {name}")

    boundary = ROOT / "forge" / "PUBLIC_PRIVATE_BOUNDARY.md"
    if not boundary.is_file():
        failures.append("missing forge/PUBLIC_PRIVATE_BOUNDARY.md")
    else:
        text = boundary.read_text(encoding="utf-8")
        for key in sorted(REQUIRED_ROOT_BOUNDARY_KEYS):
            if key not in text:
                failures.append(f"public boundary missing: {key}")

    release_boundaries = sorted((ROOT / "releases").glob("*/PUBLIC_BOUNDARY.yml"))
    if not release_boundaries:
        failures.append("no release-specific PUBLIC_BOUNDARY.yml files found")
    for release_boundary in release_boundaries:
        text = release_boundary.read_text(encoding="utf-8")
        relative = release_boundary.relative_to(ROOT).as_posix()
        for key in sorted(REQUIRED_RELEASE_BOUNDARY_KEYS):
            if key not in text:
                failures.append(f"{relative} missing: {key}")
        if not any(
            key in text
            for key in ("phase36_37_custody_present: true", "phase38_lineage_present: true")
        ):
            failures.append(f"{relative} missing Phase 36/37 custody or Phase 38 lineage")
        if "human_release_approved: true" not in text and "human_release_approved: false" not in text:
            failures.append(f"{relative} missing explicit human release approval state")

    custody_text = (ROOT / "CUSTODY.md").read_text(encoding="utf-8")
    for term in ("Phase 36", "Phase 37", "Frazer Σ Love ACO-Σ", "Sara ΣΩ"):
        if term not in custody_text:
            failures.append(f"custody surface missing: {term}")

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix().lower()
        for marker in PROTECTED_PATH_MARKERS:
            if marker in relative:
                failures.append(f"protected path marker present: {relative}")

    if failures:
        print("BOUNDARY CHECK FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("BOUNDARY CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
