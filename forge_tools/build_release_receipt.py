# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Create an observational hash manifest for a weekly release directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "build"}


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def candidate_paths(release: pathlib.Path) -> list[pathlib.Path]:
    """Use Git custody for a root receipt; release receipts remain archive-capable."""
    if release == ROOT and (ROOT / ".git").is_dir():
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        return [ROOT / item.decode() for item in result.stdout.split(b"\0") if item]
    return list(release.rglob("*"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("release", help="Release directory relative to repository root")
    parser.add_argument("--output", default="release-receipt.json")
    args = parser.parse_args()

    release = (ROOT / args.release).resolve()
    if (release != ROOT and ROOT not in release.parents) or not release.is_dir():
        raise SystemExit("release must be an existing directory inside the repository")

    output = (ROOT / args.output).resolve()
    if output != ROOT and ROOT not in output.parents:
        raise SystemExit("output must remain inside the repository")

    files = []
    for path in sorted(candidate_paths(release)):
        if (
            path.is_file()
            and path.resolve() != output
            and not any(part in SKIP_DIRS or part.endswith(".egg-info") for part in path.parts)
        ):
            files.append({
                "path": path.relative_to(release).as_posix(),
                "sha256": digest(path),
                "bytes": path.stat().st_size,
            })

    receipt = {
        "$comment": "SPDX-License-Identifier: Apache-2.0",
        "schema": "BLOOMCORE_NOW.RELEASE_INTEGRITY_RECEIPT.v2",
        "generation": "DETERMINISTIC_CONTENT_MANIFEST",
        "release": release.relative_to(ROOT).as_posix(),
        "file_count": len(files),
        "files": files,
        "claims": {
            "file_integrity_only": True,
            "truth_certified": False,
            "identity_certified": False,
            "semantic_continuity_certified": False,
        },
    }
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
