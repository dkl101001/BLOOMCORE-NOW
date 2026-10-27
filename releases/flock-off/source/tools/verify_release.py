#!/usr/bin/env python3
"""Verify the clean FLOCK OFF source repository without network access."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

APACHE_2_LICENSE_SHA256 = "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
AGPL_LICENSE_SHA256 = "8efd18c6e6527d9f853673c691ebbc0fc017b7a549c26b834f93bb0645b7093e"
BLOCKED_IMPORTS = {"socket", "requests", "urllib", "http", "httpx", "aiohttp", "scapy", "bluetooth", "pcap"}
NETWORK_BOUNDARIES = {
    'flockoff_collaboration/transport.py': {'requests'},
    'flockoff_collaboration/mailbox.py': {'http.server'},
    'flockoff_research/agent.py': {'requests'},
}
ALLOWED_ROOT_ENTRIES = {
    ".gitignore", "AUTHORS.md", "BUILD.md", "LICENSE", "LICENSES", "MANIFEST.sha256",
    "NOTICE", "README.md", "SCHEMAS", "SECURITY.md", "SIGNATURES", "TESTS",
    "THIRD_PARTY_NOTICES", "config", "docs", "hardware_profiles",
    "pyproject.toml", "requirements.lock", "src", "tools", "PACKAGING_ALLOWLIST.json",
}
GENERATED_PARTS = {".venv", "__pycache__", "build", "dist", "work"}


def included(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return (
        path.is_file()
        and not any(part in GENERATED_PARTS or part.endswith(".egg-info") for part in relative.parts)
        and not path.name.endswith((".pyc", ".pyo"))
    )


def verify_json_and_python() -> tuple[int, int]:
    json_files = 0
    python_files = 0
    for path in ROOT.rglob("*"):
        if not included(path):
            continue
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
            json_files += 1
        elif path.suffix == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    json.loads(line)
            json_files += 1
        elif path.suffix in (".py", ".pyw"):
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            python_files += 1
    return json_files, python_files


def verify_runtime_imports() -> None:
    findings: list[str] = []
    for path in (ROOT / "src").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name in NETWORK_BOUNDARIES.get(path.relative_to(ROOT / 'src').as_posix(),set()):
                    continue
                if name.split(".")[0] in BLOCKED_IMPORTS and not (isinstance(node, ast.ImportFrom) and node.module == "urllib.parse") :
                    findings.append(f"{path.relative_to(ROOT)}:{name}")
    if findings:
        raise RuntimeError(f"network-capable imports in active runtime: {findings}")


def verify_repository_shape() -> None:
    if not (ROOT / "README.md").is_file():
        raise RuntimeError("README.md is missing from repository root")
    unexpected = sorted(
        item.name for item in ROOT.iterdir()
        if item.name not in ALLOWED_ROOT_ENTRIES
        and item.name not in GENERATED_PARTS
        and not item.name.endswith(".egg-info")
    )
    if unexpected:
        raise RuntimeError(f"unexpected repository-root entries: {unexpected}")
    license_hash = hashlib.sha256((ROOT / "LICENSE").read_bytes()).hexdigest()
    if license_hash != AGPL_LICENSE_SHA256:
        raise RuntimeError("LICENSE is not the pinned combined AGPL-3.0-only text")
    if hashlib.sha256((ROOT/'LICENSES/Apache-2.0.txt').read_bytes()).hexdigest()!=APACHE_2_LICENSE_SHA256:
        raise RuntimeError('Historical Apache license changed')


def run_tests() -> int:
    suite = unittest.defaultTestLoader.discover(str(ROOT / "TESTS"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError(
            f"tests failed: failures={len(result.failures)} errors={len(result.errors)}"
        )
    return result.testsRun


def main() -> int:
    verify_repository_shape()
    json_files, python_files = verify_json_and_python()
    verify_runtime_imports()
    tests = run_tests()
    print(json.dumps({
        "status": "ok",
        "tests": tests,
        "json_or_jsonl_files": json_files,
        "python_files": python_files,
        "active_runtime_network_import_findings": [],
        "license": "AGPL-3.0-only combined distribution; original Apache notices retained",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
