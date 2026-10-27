"""Offline command-line entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from .crypto import FieldCipher
from .ledger import EvidenceLedger
from .live import (
    LiveRealityLoop, TargetExpectation, iter_live_sources, iter_named_sources,
    strict_json_object,
)
from .live_remote_id import RemoteIDLiveLoop
from .replay import run_records
from .schema_guard import ValidationError, validate
from .signatures import signature_content_hash

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BUNDLED_ROOT = Path(__file__).resolve().parent / "resources"
PACKAGE_ROOT = SOURCE_ROOT if (SOURCE_ROOT / "SCHEMAS").is_dir() else BUNDLED_ROOT


def _strict_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load_jsonl(path: Path) -> list[dict]:
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        if len(line.encode("utf-8")) > 1_048_576:
            raise ValueError(f"line {number} exceeds 1 MiB ingest limit")
        records.append(json.loads(
            line,
            object_pairs_hook=_strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        ))
    return records


def _load_json(path: Path) -> dict:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_strict_object,
        parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
    )
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _runtime_secrets() -> tuple[bytes, str]:
    secret_hex = os.environ.get("FLOCKOFF_ROTATION_SECRET_HEX")
    if secret_hex is None:
        raise RuntimeError("FLOCKOFF_ROTATION_SECRET_HEX is required (at least 32 random bytes)")
    secret = bytes.fromhex(secret_hex)
    if len(secret) < 32:
        raise RuntimeError("FLOCKOFF_ROTATION_SECRET_HEX must decode to at least 32 bytes")
    route_key = os.environ.get("FLOCKOFF_ROUTE_KEY_BASE64")
    if route_key is None:
        raise RuntimeError("FLOCKOFF_ROUTE_KEY_BASE64 is required for the encrypted route vault")
    return secret, route_key


def _validated_signature(path: Path, schema_path: Path | None = None) -> dict:
    signature = _load_json(path)
    signature_schema = _load_json(
        schema_path or PACKAGE_ROOT / "SCHEMAS" / "signature.schema.json"
    )
    validate(signature, signature_schema)
    if signature["provenance"]["content_hash"] != signature_content_hash(signature):
        raise ValueError("signature content hash mismatch")
    return signature


def command_replay(args: argparse.Namespace) -> int:
    signature = _validated_signature(args.signature, args.signature_schema)
    secret, route_key = _runtime_secrets()
    result = run_records(
        _load_jsonl(args.input), signature=signature, rotation_secret=secret,
        include_restricted=True,
    )
    migration = PACKAGE_ROOT / "SCHEMAS" / "migrations" / "0001_initial.sql"
    with EvidenceLedger(
        args.ledger, migration, FieldCipher.from_base64(route_key),
        evidence_digest_secret=secret,
    ) as ledger:
        for pose in result["poses"]:
            ledger.append_restricted_pose(pose)
        event_groups = [
            ("measurement_lineage", "measurement_lineage_id", result["measurement_lineages"]),
            ("observation", "observation_id", result["observations"]),
            ("signature_match", "match_id", result["signature_matches"]),
            ("pose_association", "association_id", result["pose_associations"]),
            ("pass_partition", "partition_id", result["pass_partitions"]),
            ("evidence_receipt", "receipt_id", result["receipts"]),
        ]
        for kind, id_field, items in event_groups:
            for item in items:
                ledger.append_event(kind, item[id_field], item)
        for node in result["node_revisions"]:
            ledger.append_node_revision(node)
    result.pop("poses")
    payload = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


def command_live_flock_you(args: argparse.Namespace) -> int:
    signature = _validated_signature(args.signature, args.signature_schema)
    targets_doc = _load_json(args.targets)
    targets_raw = targets_doc.get("targets")
    if not isinstance(targets_raw, list) or not targets_raw:
        raise ValueError("targets file must contain a non-empty 'targets' array")
    target_schema = _load_json(PACKAGE_ROOT / "SCHEMAS" / "target_expectation.schema.json")
    expectations = []
    for index, item in enumerate(targets_raw):
        if not isinstance(item, dict):
            raise ValueError(f"target {index} is not a JSON object")
        validate(item, target_schema)
        expectations.append(TargetExpectation.from_dict(item))

    secret, route_key = _runtime_secrets()
    migration = PACKAGE_ROOT / "SCHEMAS" / "migrations" / "0001_initial.sql"
    output_handle = args.output.open("a", encoding="utf-8") if args.output else sys.stdout

    def emit(item: dict) -> None:
        output_handle.write(json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
        output_handle.flush()

    try:
        with EvidenceLedger(
            args.ledger, migration, FieldCipher.from_base64(route_key),
            evidence_digest_secret=secret,
        ) as ledger:
            loop = LiveRealityLoop(
                signature=signature, expectations=expectations, receiver_id=args.receiver_id,
                hardware_profile_id=args.hardware_profile_id, rotation_epoch=args.rotation_epoch,
                rotation_secret=secret, ledger=ledger, max_pose_age_seconds=args.max_pose_age_seconds,
                upstream_build_ref=args.flock_you_build_ref, session_id=args.session_id,
            )
            try:
                for source, line in iter_live_sources(
                    flock_you_path=args.flock_you_input, pose_path=args.pose_input, baud=args.baud
                ):
                    try:
                        record = strict_json_object(line)
                        if source == "pose":
                            generated = loop.ingest_pose(record)
                        else:
                            generated = loop.ingest_flock_you(
                                record, received_at_utc=_utc_now_for_cli(),
                                host_monotonic_ns=time.monotonic_ns(),
                            )
                        for item in generated:
                            emit(item)
                    except (ValueError, ValidationError) as exc:
                        if source == "flock_you":
                            loop.mark_quarantined()
                        emit({
                            "kind": "quarantined_input", "source": source,
                            "reason": str(exc), "absence_claim_permitted": False,
                        })
            finally:
                for item in loop.flush():
                    emit(item)
                loop.mark_sensor_disconnected()
    finally:
        if args.output:
            output_handle.close()
    return 0


def command_live_remote_id(args: argparse.Namespace) -> int:
    """Run the v0.3 decoded live Remote ID path without network access."""

    secret, route_key = _runtime_secrets()
    migration = PACKAGE_ROOT / "SCHEMAS" / "migrations" / "0001_initial.sql"
    output_handle = args.output.open("a", encoding="utf-8") if args.output else sys.stdout

    def emit(item: dict) -> None:
        output_handle.write(
            json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        )
        output_handle.flush()

    try:
        with EvidenceLedger(
            args.ledger, migration, FieldCipher.from_base64(route_key),
            evidence_digest_secret=secret,
        ) as ledger:
            loop = RemoteIDLiveLoop(
                receiver_id=args.receiver_id,
                hardware_profile_id=args.hardware_profile_id,
                rotation_epoch=args.rotation_epoch,
                rotation_secret=secret,
                ledger=ledger,
                max_pose_age_seconds=args.max_pose_age_seconds,
                max_source_clock_skew_seconds=args.max_source_clock_skew_seconds,
                upstream_receiver_revision=args.remote_id_receiver_build_ref,
                upstream_core_revision=args.remote_id_core_build_ref,
                session_id=args.session_id,
            )
            try:
                for source, line in iter_named_sources(
                    sensor_name="remote_id", sensor_path=args.remote_id_input,
                    pose_path=args.pose_input, baud=args.baud,
                ):
                    try:
                        record = strict_json_object(line)
                        if source == "pose":
                            generated = loop.ingest_pose(record)
                        elif record.get("event") == "receiver_status":
                            generated = loop.ingest_status(
                                record, received_at_utc=_utc_now_for_cli()
                            )
                        elif record.get("event") in {"remote_id", "remote_id_message"}:
                            generated = loop.ingest_remote_id(
                                record, received_at_utc=_utc_now_for_cli(),
                                host_monotonic_ns=time.monotonic_ns(),
                            )
                        else:
                            raise ValueError(
                                "Remote ID input event must be remote_id, "
                                "remote_id_message, or receiver_status"
                            )
                        for item in generated:
                            emit(item)
                    except (ValueError, ValidationError) as exc:
                        if source == "remote_id":
                            loop.mark_quarantined()
                        emit({
                            "kind": "quarantined_input", "source": source,
                            "reason": str(exc), "absence_claim_permitted": False,
                        })
            finally:
                for item in loop.flush():
                    emit(item)
    finally:
        if args.output:
            output_handle.close()
    return 0


def _utc_now_for_cli() -> str:
    import datetime as dt
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def command_validate(args: argparse.Namespace) -> int:
    instance = _load_json(args.instance)
    schema = _load_json(args.schema)
    validate(instance, schema)
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="FLOCK OFF offline evidence runtime")
    sub = root.add_subparsers(dest="command", required=True)
    replay = sub.add_parser("replay", help="replay an NDJSON fixture without network access")
    replay.add_argument("--input", type=Path, required=True)
    replay.add_argument("--signature", type=Path, required=True)
    replay.add_argument("--signature-schema", type=Path)
    replay.add_argument("--ledger", type=Path, required=True,
                        help="append-only SQLite ledger; receiver poses are encrypted")
    replay.add_argument("--output", type=Path)
    replay.set_defaults(func=command_replay)
    live = sub.add_parser(
        "live-flock-you",
        help="consume a receive-only live Flock-You NDJSON/USB feed and recurse on bounded misses",
    )
    live.add_argument("--flock-you-input", required=True,
                      help="USB CDC device, FIFO, regular NDJSON file, or '-' for stdin")
    live.add_argument("--pose-input", required=True,
                      help="local GNSS pose NDJSON device/FIFO/file; cannot share stdin with sensor")
    live.add_argument("--baud", type=int, default=115200)
    live.add_argument("--targets", type=Path, required=True)
    live.add_argument("--signature", type=Path, required=True)
    live.add_argument("--signature-schema", type=Path)
    live.add_argument("--ledger", type=Path, required=True)
    live.add_argument("--receiver-id", required=True)
    live.add_argument("--hardware-profile-id", default="xiao-esp32s3-flock-you-2g4")
    live.add_argument("--rotation-epoch", default="live-session-1")
    live.add_argument("--session-id")
    live.add_argument("--max-pose-age-seconds", type=float, default=3.0)
    live.add_argument("--flock-you-build-ref", default="UNVERIFIED_LIVE_FEED",
                      help="operator-supplied flashed build/commit reference; never inferred from the stream")
    live.add_argument("--output", type=Path)
    live.set_defaults(func=command_live_flock_you)
    remote = sub.add_parser(
        "live-remote-id",
        help="consume decoded receive-only Remote ID NDJSON and build private mobile tracks",
    )
    remote.add_argument("--remote-id-input", required=True,
                        help="local decoded NDJSON device, FIFO, file, or '-' for stdin")
    remote.add_argument("--pose-input", required=True,
                        help="separate observer GNSS pose NDJSON device/FIFO/file")
    remote.add_argument("--baud", type=int, default=115200)
    remote.add_argument("--ledger", type=Path, required=True)
    remote.add_argument("--receiver-id", required=True)
    remote.add_argument("--hardware-profile-id", default="opendroneid-external-decoded-v3.7.0")
    remote.add_argument("--rotation-epoch", default="live-rid-session-1")
    remote.add_argument("--session-id")
    remote.add_argument("--max-pose-age-seconds", type=float, default=3.0)
    remote.add_argument("--max-source-clock-skew-seconds", type=float, default=5.0)
    remote.add_argument("--remote-id-receiver-build-ref", default="v3.7.0@60b4320",
                        help="actual upstream receiver build/tag; never inferred")
    remote.add_argument("--remote-id-core-build-ref", default="master@ec44332",
                        help="actual OpenDroneID core revision used by the upstream decoder")
    remote.add_argument("--output", type=Path)
    remote.set_defaults(func=command_live_remote_id)
    tape = sub.add_parser("red-tape", help="local Transparency Desk and Red Tape Dispenser")
    tape.add_argument("args", nargs=argparse.REMAINDER)
    guard = sub.add_parser("validate", help="validate one JSON instance")
    guard.add_argument("--instance", type=Path, required=True)
    guard.add_argument("--schema", type=Path, required=True)
    guard.set_defaults(func=command_validate)
    return root


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "red-tape":
        from flockoff_red_tape.cli import main as red_tape_main
        return red_tape_main(argv[1:])
    try:
        args = parser().parse_args(argv)
        return args.func(args)
    except (ValueError, RuntimeError, ValidationError) as exc:
        print(f"flockoff: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
