# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Command-line interface for BLOOMCORE RECEIPT."""

from __future__ import annotations

import argparse
import pathlib
import sys

from bloomcore_receipt import audit_text, render_json, render_markdown


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect citation surfaces and emit observational evidence receipts."
    )
    parser.add_argument("input", help="UTF-8 text or Markdown input file, or '-' for stdin")
    parser.add_argument("--offline", action="store_true", help="Do not fetch citation targets")
    parser.add_argument("--json-out", help="Write the JSON receipt to this path")
    parser.add_argument("--markdown-out", help="Write the Markdown receipt to this path")
    args = parser.parse_args()

    if args.input == "-":
        text = sys.stdin.read()
    else:
        text = pathlib.Path(args.input).read_text(encoding="utf-8")

    receipt = audit_text(text, online=not args.offline)
    json_text = render_json(receipt)
    markdown_text = render_markdown(receipt)

    if args.json_out:
        pathlib.Path(args.json_out).write_text(json_text, encoding="utf-8")
    if args.markdown_out:
        pathlib.Path(args.markdown_out).write_text(markdown_text, encoding="utf-8")
    if not args.json_out and not args.markdown_out:
        sys.stdout.write(markdown_text)

    return 2 if receipt["summary"]["red_flags"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

