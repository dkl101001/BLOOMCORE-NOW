# SPDX-License-Identifier: MPL-2.0
"""Command-line interface for reconstruction-preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core import ManifestError, canonical_bytes, evaluate_manifest, load_manifest, verify_receipt


def _validate(args: argparse.Namespace) -> int:
    try:
        manifest, path, digest = load_manifest(args.manifest)
        evaluation = evaluate_manifest(manifest, manifest_path=path, input_sha256=digest)
    except (OSError, ManifestError) as exc:
        print(f"INVALID_INPUT: {exc}", file=sys.stderr)
        return 4
    receipt = evaluation.receipt_with_hash()
    payload = canonical_bytes(receipt)
    if args.receipt:
        destination = Path(args.receipt)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
    sys.stdout.buffer.write(payload)
    return {
        "VERIFIED_FOR_BUILD_SCOPE": 0,
        "PARTIAL_BUT_INDEPENDENT_WORK_SAFE": 2,
        "RECONSTRUCTION_BLOCKED": 3,
    }[evaluation.disposition]


def _verify(args: argparse.Namespace) -> int:
    try:
        value = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"INVALID_RECEIPT: {exc}", file=sys.stderr)
        return 4
    valid, detail = verify_receipt(value)
    if not valid:
        print(f"INVALID_RECEIPT: {detail}", file=sys.stderr)
        return 3
    print(f"VALID {detail}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reconstruction-preflight",
        description="Check bounded reconstruction evidence before dependency-bearing work.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="evaluate a preflight manifest")
    validate.add_argument("manifest")
    validate.add_argument("--receipt", help="write canonical JSON receipt")
    validate.set_defaults(handler=_validate)
    verify = subparsers.add_parser("verify-receipt", help="verify a deterministic receipt hash")
    verify.add_argument("receipt")
    verify.set_defaults(handler=_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())

