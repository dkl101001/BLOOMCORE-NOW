#!/usr/bin/env python3
"""Build a deterministic source ZIP whose root opens directly to README.md."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = (2026, 10, 27, 0, 0, 0)
GENERATED_PARTS = {".venv", "__pycache__", "build", "dist", "work"}
EXCLUDED_NAMES = {"MANIFEST.sha256"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def included(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return (
        path.is_file()
        and relative.as_posix() in json.loads((ROOT / 'PACKAGING_ALLOWLIST.json').read_text(encoding='utf-8'))['paths']
        and relative.as_posix() not in EXCLUDED_NAMES
        and not any(part in GENERATED_PARTS or part.endswith(".egg-info") for part in relative.parts)
        and not path.name.endswith((".pyc", ".pyo", ".zip"))
    )


def build(output: Path) -> None:
    approved=set(json.loads((ROOT/'PACKAGING_ALLOWLIST.json').read_text(encoding='utf-8'))['paths'])
    for name in approved:
        candidate=(ROOT/name).resolve()
        if not candidate.is_relative_to(ROOT.resolve()) or not candidate.is_file():
            raise RuntimeError('Invalid allowlisted source path: '+name)
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "verify_release.py")],
        cwd=ROOT,
        check=True,
    )
    files = sorted(path for path in ROOT.rglob("*") if included(path))
    manifest = ROOT / "MANIFEST.sha256"
    manifest.write_text(
        "\n".join(f"{digest(path)}  {path.relative_to(ROOT).as_posix()}" for path in files)
        + "\n",
        encoding="utf-8",
    )
    archive_files = [*files, manifest]
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in archive_files:
            info = zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        if "README.md" not in names or any(name.startswith("FLOCK_OFF_") for name in names):
            raise RuntimeError("source ZIP root is not clean")
    print(f"{output} sha256:{digest(output)} files:{len(archive_files)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path,
        default=ROOT.parent / "FLOCK_OFF_v0.3.0_collaboration.1_EXPERIMENTAL_SOURCE.zip",
    )
    args = parser.parse_args()
    build(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
