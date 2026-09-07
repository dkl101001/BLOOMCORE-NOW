# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Command-line interface for BLOOMCORE SBOM RECEIPT."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Sequence

from .core import PROFILE_NAME, PROFILE_URL, inspect_bytes, render_markdown, verify_receipt


def _write_new(path: pathlib.Path, content: str) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content)
    except FileExistsError as exc:
        raise FileExistsError(f"refusing to overwrite existing path: {path}") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sbom-receipt", description="Create deterministic CISA 2026 SBOM structural receipts.")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="inspect CycloneDX JSON")
    check.add_argument("input", type=pathlib.Path)
    check.add_argument("--json", dest="json_output", type=pathlib.Path)
    check.add_argument("--markdown", dest="markdown_output", type=pathlib.Path)
    check.add_argument("--advisory", action="store_true", help="return zero even when structural gaps are found")
    verify = sub.add_parser("verify", help="verify a receipt self-hash")
    verify.add_argument("receipt", type=pathlib.Path)
    sub.add_parser("profile", help="print the bounded profile identity")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "profile":
            print(json.dumps({"name": PROFILE_NAME, "source": PROFILE_URL, "scope": "structural-presence-only"}, sort_keys=True))
            return 0
        if args.command == "verify":
            receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
            valid = verify_receipt(receipt)
            print("RECEIPT VERIFIED" if valid else "RECEIPT INVALID")
            return 0 if valid else 1

        receipt = inspect_bytes(args.input.read_bytes())
        json_text = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.json_output:
            _write_new(args.json_output, json_text)
        if args.markdown_output:
            _write_new(args.markdown_output, render_markdown(receipt))
        if not args.json_output and not args.markdown_output:
            sys.stdout.write(json_text)
        summary = receipt["summary"]
        print(
            f"SBOM RECEIPT: {summary['missing']} missing, "
            f"{summary['explicit_unknown']} explicit unknown, "
            f"{summary['not_machine_verifiable']} not machine-verifiable",
            file=sys.stderr,
        )
        return 0 if args.advisory or summary["structurally_complete"] else 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
