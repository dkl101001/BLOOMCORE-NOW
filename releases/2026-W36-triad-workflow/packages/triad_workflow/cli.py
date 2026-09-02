# SPDX-License-Identifier: MPL-2.0
"""Command-line interface for bounded Triad-derived workflow packets."""

from __future__ import annotations

import argparse
import pathlib
import sys

from .core import WorkflowError, build_artifacts, load_json, replay_packet, validate_packet, verify_run


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="triad-workflow")
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("validate", "run", "replay"):
        command = commands.add_parser(name)
        command.add_argument("input", type=pathlib.Path)
        if name == "run":
            command.add_argument("--out", required=True, type=pathlib.Path)
        if name == "replay":
            command.add_argument("run_dir", type=pathlib.Path)
    verify = commands.add_parser("verify")
    verify.add_argument("run_dir", type=pathlib.Path)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "verify":
            verify_run(args.run_dir)
            print("VERIFIED: receipt and run artifacts are internally consistent")
            return 0
        packet_path = args.input.resolve()
        packet = load_json(packet_path)
        if args.command == "validate":
            validate_packet(packet, packet_path.parent)
            print("VALID: bounded Triad workflow packet")
        elif args.command == "run":
            if args.out.exists():
                raise WorkflowError(f"refusing to overwrite existing output path: {args.out}")
            artifacts = build_artifacts(packet, packet_path.parent)
            args.out.mkdir(parents=True)
            for name, content in artifacts.items():
                (args.out / name).write_bytes(content)
            print(f"WROTE: {args.out} ({len(artifacts)} deterministic artifacts)")
        else:
            replay_packet(packet, packet_path.parent, args.run_dir)
            print("REPLAY VERIFIED: input reproduces all run artifacts byte-for-byte")
    except WorkflowError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0
