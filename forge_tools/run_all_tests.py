# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Run every weekly release test suite without third-party test dependencies."""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(command: list[str]) -> int:
    print(f"+ {' '.join(command)}")
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def main() -> int:
    test_suites = sorted(
        path for path in (ROOT / "releases").glob("*/tests") if path.is_dir()
    )
    if not test_suites:
        print("NO RELEASE TEST SUITES FOUND")
        return 1
    commands = [
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            suite.relative_to(ROOT).as_posix(),
            "-v",
        ]
        for suite in test_suites
    ]
    commands.extend([
        [sys.executable, "forge_tools/check_licenses.py"],
        [sys.executable, "forge_tools/check_boundaries.py"],
    ])
    for command in commands:
        code = run(command)
        if code:
            return code
    print("ALL FOUNDRY TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
