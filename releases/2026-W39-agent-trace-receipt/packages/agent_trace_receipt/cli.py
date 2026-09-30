# SPDX-License-Identifier: MPL-2.0
"""CLI for BLOOMCORE Agent Trace Receipt."""

from __future__ import annotations

import argparse
import pathlib
import sys

from .core import TraceError, build_artifacts, load_policy, load_trace, replay, verify_run


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="agent-trace-receipt")
    commands = result.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate a policy and JSONL trace")
    validate.add_argument("policy", type=pathlib.Path)
    validate.add_argument("trace", type=pathlib.Path)
    audit = commands.add_parser("audit", help="write deterministic receipt artifacts")
    audit.add_argument("policy", type=pathlib.Path)
    audit.add_argument("trace", type=pathlib.Path)
    audit.add_argument("--out", required=True, type=pathlib.Path)
    audit.add_argument("--strict", action="store_true", help="exit 1 for violations or unknown events after writing")
    verify = commands.add_parser("verify", help="verify receipt integrity and bounded claims")
    verify.add_argument("run_dir", type=pathlib.Path)
    replay_command = commands.add_parser("replay", help="rebuild and compare receipt artifacts")
    replay_command.add_argument("policy", type=pathlib.Path)
    replay_command.add_argument("trace", type=pathlib.Path)
    replay_command.add_argument("run_dir", type=pathlib.Path)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "validate":
            load_policy(args.policy)
            load_trace(args.trace)
            print("VALID: policy and trace are structurally readable")
            return 0
        if args.command == "verify":
            receipt = verify_run(args.run_dir)
            print(f"VERIFIED: {receipt['verdict']} receipt is internally consistent")
            return 0
        if args.command == "replay":
            replay(args.policy, args.trace, args.run_dir)
            print("REPLAY VERIFIED: inputs reproduce all artifacts byte-for-byte")
            return 0
        if args.out.exists():
            raise TraceError(f"refusing to overwrite existing output path: {args.out}")
        artifacts = build_artifacts(args.policy, args.trace)
        args.out.mkdir(parents=True)
        for name, content in artifacts.items():
            (args.out / name).write_bytes(content)
        receipt = verify_run(args.out)
        print(f"WROTE: {args.out} — {receipt['verdict']} ({receipt['counts']['events']} events)")
        if args.strict and (receipt["counts"]["VIOLATION"] or receipt["counts"]["UNKNOWN"]):
            return 1
        return 0
    except TraceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

