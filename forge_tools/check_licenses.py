# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Deterministically verify the repository's file-level license membrane."""

from __future__ import annotations

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
    ("forge_tools/", "MPL-2.0"),
    ("shared/deterministic-tools/", "MPL-2.0"),
    ("shared/runtime-contracts/", "AGPL-3.0-only"),
    ("releases/2026-W31-bloomcore-receipt/apps/receipt-server/", "AGPL-3.0-only"),
    ("releases/2026-W31-bloomcore-receipt/packages/evidence-validator/", "MPL-2.0"),
    ("releases/2026-W31-bloomcore-receipt/packages/receipt-schema/", "Apache-2.0"),
    ("releases/2026-W31-bloomcore-receipt/examples/", "Apache-2.0"),
)


def expected_license(relative: str) -> str | None:
    for prefix, license_id in PATH_RULES:
        if relative.startswith(prefix):
            return license_id
    return None


def iter_text_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if "LICENSES" in path.parts or path.name in {"NOTICE"}:
            continue
        if path.suffix in TEXT_SUFFIXES or path.name in SPECIAL_TEXT:
            files.append(path)
    return sorted(files)


def main() -> int:
    failures: list[str] = []
    for path in iter_text_files():
        relative = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        if "SPDX-License-Identifier:" not in text[:600]:
            failures.append(f"{relative}: missing SPDX identifier near file start")
            continue
        required = expected_license(relative)
        if required and f"SPDX-License-Identifier: {required}" not in text[:600]:
            failures.append(f"{relative}: expected {required}")

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

