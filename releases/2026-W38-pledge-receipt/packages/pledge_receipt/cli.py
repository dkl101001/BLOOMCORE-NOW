# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Command-line interface for BLOOMCORE PLEDGE RECEIPT."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from .core import (
    audit_packet,
    diff_packets,
    inspect_json_bytes,
    render_markdown,
    scaffold_markdown,
    verify_receipt,
)


def _write(path: str | None, content: str) -> None:
    if path is None:
        return
    destination = pathlib.Path(path)
    if destination.exists():
        raise ValueError(f"refusing to overwrite existing output: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pledge-receipt")
    sub = parser.add_subparsers(dest="command", required=True)

    scaffold = sub.add_parser("scaffold", help="extract candidate pledge statements from Markdown")
    scaffold.add_argument("source")
    scaffold.add_argument("--title", required=True)
    scaffold.add_argument("--issuer", required=True)
    scaffold.add_argument("--version", required=True)
    scaffold.add_argument("--url", required=True)
    scaffold.add_argument("--published")
    scaffold.add_argument("--json", required=True)

    audit = sub.add_parser("audit", help="audit a structured pledge packet")
    audit.add_argument("packet")
    audit.add_argument("--source", help="optional original source for SHA-256 correspondence")
    audit.add_argument("--json")
    audit.add_argument("--markdown")
    audit.add_argument("--advisory", action="store_true", help="return success even with structural gaps")

    diff = sub.add_parser("diff", help="compare two structured pledge packet versions")
    diff.add_argument("before")
    diff.add_argument("after")
    diff.add_argument("--json")
    diff.add_argument("--markdown")
    diff.add_argument("--advisory", action="store_true", help="return success despite weakening signals")

    verify = sub.add_parser("verify", help="verify a receipt self-hash")
    verify.add_argument("receipt")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "scaffold":
            raw = pathlib.Path(args.source).read_bytes()
            packet = scaffold_markdown(
                raw,
                title=args.title,
                issuer=args.issuer,
                version=args.version,
                source_url=args.url,
                published=args.published,
            )
            _write(args.json, _json(packet))
            print(f"SCAFFOLDED {len(packet['commitments'])} CANDIDATE COMMITMENTS")
            return 0
        if args.command == "audit":
            packet = inspect_json_bytes(pathlib.Path(args.packet).read_bytes())
            source = pathlib.Path(args.source).read_bytes() if args.source else None
            receipt = audit_packet(packet, source)
            _write(args.json, _json(receipt))
            _write(args.markdown, render_markdown(receipt))
            print(_json(receipt), end="")
            return 0 if args.advisory or receipt["summary"]["active_structural_gaps"] == 0 else 1
        if args.command == "diff":
            before = inspect_json_bytes(pathlib.Path(args.before).read_bytes())
            after = inspect_json_bytes(pathlib.Path(args.after).read_bytes())
            receipt = diff_packets(before, after)
            _write(args.json, _json(receipt))
            _write(args.markdown, render_markdown(receipt))
            print(_json(receipt), end="")
            return 0 if args.advisory or receipt["summary"]["structural_weakening_signals"] == 0 else 1
        if args.command == "verify":
            receipt = inspect_json_bytes(pathlib.Path(args.receipt).read_bytes())
            if verify_receipt(receipt):
                print("VERIFIED — deterministic receipt self-hash matches")
                return 0
            print("FAILED — receipt self-hash mismatch", file=sys.stderr)
            return 1
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    raise AssertionError("unreachable")
