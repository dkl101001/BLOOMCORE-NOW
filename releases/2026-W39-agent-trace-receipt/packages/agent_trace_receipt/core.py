# SPDX-License-Identifier: MPL-2.0
"""Deterministic, passive comparison of declared agent scope and event traces."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import pathlib
import re
from typing import Any

VERSION = "0.1.0"
POLICY_SCHEMA = "BLOOMCORE_NOW.AGENT_TRACE_POLICY.v1"
RECEIPT_SCHEMA = "BLOOMCORE_NOW.AGENT_TRACE_RECEIPT.v1"
MANIFEST_SCHEMA = "BLOOMCORE_NOW.AGENT_TRACE_MANIFEST.v1"
KINDS = ("file_read", "file_write", "file_delete", "command", "network_host", "tool")
DECISIONS = ("ALLOWED", "VIOLATION", "UNKNOWN")
MAX_INPUT_BYTES = 5 * 1024 * 1024
MAX_EVENTS = 50_000
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class TraceError(ValueError):
    """A bounded input or verification failure."""


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_bounded(path: pathlib.Path) -> bytes:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise TraceError(str(exc)) from exc
    if size > MAX_INPUT_BYTES:
        raise TraceError(f"input exceeds {MAX_INPUT_BYTES} bytes: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise TraceError(str(exc)) from exc


def _pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values:
        if key in result:
            raise TraceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise TraceError(f"non-finite JSON number is forbidden: {value}")


def _decode_json(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_invalid_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TraceError(f"{label}: {exc}") from exc


def load_policy(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    raw = _read_bounded(path)
    value = _decode_json(raw, "policy")
    if not isinstance(value, dict):
        raise TraceError("policy must be a JSON object")
    validate_policy(value)
    return value, raw


def load_trace(path: pathlib.Path) -> tuple[list[dict[str, Any]], bytes]:
    raw = _read_bounded(path)
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        if len(events) >= MAX_EVENTS:
            raise TraceError(f"trace exceeds {MAX_EVENTS} events")
        value = _decode_json(line, f"trace line {line_number}")
        if not isinstance(value, dict):
            raise TraceError(f"trace line {line_number}: event must be an object")
        value = dict(value)
        value["_line"] = line_number
        events.append(value)
    if not events:
        raise TraceError("trace must contain at least one JSON event")
    return events, raw


def _exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise TraceError(f"{label} keys differ; missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TraceError(f"{label} must be a non-empty string")
    if any(ord(char) < 32 for char in value):
        raise TraceError(f"{label} contains control characters")
    return value


def validate_policy(policy: dict[str, Any]) -> None:
    _exact_keys(policy, {"$comment", "schema", "run_id", "actor", "allowed", "unknown_kinds"}, "policy")
    if policy["$comment"] != "SPDX-License-Identifier: Apache-2.0":
        raise TraceError("policy $comment must carry the Apache-2.0 SPDX identifier")
    if policy["schema"] != POLICY_SCHEMA:
        raise TraceError(f"schema must be {POLICY_SCHEMA}")
    _text(policy["run_id"], "run_id")
    _text(policy["actor"], "actor")
    if policy["unknown_kinds"] not in {"UNKNOWN", "VIOLATION"}:
        raise TraceError("unknown_kinds must be UNKNOWN or VIOLATION")
    allowed = policy["allowed"]
    if not isinstance(allowed, dict):
        raise TraceError("allowed must be an object")
    _exact_keys(allowed, set(KINDS), "allowed")
    for kind in KINDS:
        patterns = allowed[kind]
        if not isinstance(patterns, list) or any(
            not isinstance(item, str)
            or not item.strip()
            or any(ord(char) < 32 for char in item)
            for item in patterns
        ):
            raise TraceError(f"allowed.{kind} must be a string list")
        if len(set(patterns)) != len(patterns):
            raise TraceError(f"allowed.{kind} contains duplicate patterns")


def _normalise_target(kind: str, target: str) -> tuple[str | None, str | None]:
    if kind.startswith("file_"):
        value = target.replace("\\", "/")
        pure = pathlib.PurePosixPath(value)
        if pure.is_absolute() or ".." in pure.parts or value in {"", "."}:
            return None, "unsafe or non-relative file target"
        return pure.as_posix(), None
    if kind == "network_host":
        value = target.lower().rstrip(".")
        if "://" in value or "/" in value or not value:
            return None, "network_host target must be a hostname only"
        return value, None
    return target.strip(), None


def _matches(kind: str, target: str, patterns: list[str]) -> bool:
    if kind == "network_host":
        for pattern in patterns:
            candidate = pattern.lower().rstrip(".")
            if candidate.startswith("*."):
                suffix = candidate[1:]
                if target.endswith(suffix) and target != suffix[1:]:
                    return True
            elif target == candidate:
                return True
        return False
    return any(fnmatch.fnmatchcase(target, pattern) for pattern in patterns)


def classify_event(policy: dict[str, Any], event: dict[str, Any], index: int) -> dict[str, Any]:
    source_line = event.get("_line")
    payload = {key: value for key, value in event.items() if key != "_line"}
    required = {"seq", "actor", "kind", "target"}
    if set(payload) != required:
        return {
            "index": index,
            "source_line": source_line,
            "seq": payload.get("seq"),
            "actor": payload.get("actor"),
            "kind": payload.get("kind"),
            "target": payload.get("target"),
            "decision": "UNKNOWN",
            "reason": f"event keys differ; missing={sorted(required-set(payload))}, extra={sorted(set(payload)-required)}",
        }
    seq, actor, kind, target = payload["seq"], payload["actor"], payload["kind"], payload["target"]
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 0:
        return {"index": index, "source_line": source_line, **payload, "decision": "UNKNOWN", "reason": "seq must be a non-negative integer"}
    if not all(isinstance(item, str) and item.strip() for item in (actor, kind, target)):
        return {"index": index, "source_line": source_line, **payload, "decision": "UNKNOWN", "reason": "actor, kind, and target must be non-empty strings"}
    if any(any(ord(char) < 32 for char in item) for item in (actor, kind, target)):
        return {"index": index, "source_line": source_line, **payload, "decision": "UNKNOWN", "reason": "actor, kind, and target cannot contain control characters"}
    if actor != policy["actor"]:
        return {"index": index, "source_line": source_line, **payload, "decision": "VIOLATION", "reason": "actor differs from declared actor"}
    if kind not in KINDS:
        return {"index": index, "source_line": source_line, **payload, "decision": policy["unknown_kinds"], "reason": "kind is not declared by this policy schema"}
    normalised, problem = _normalise_target(kind, target)
    if problem:
        return {"index": index, "source_line": source_line, **payload, "decision": "VIOLATION", "reason": problem}
    assert normalised is not None
    decision = "ALLOWED" if _matches(kind, normalised, policy["allowed"][kind]) else "VIOLATION"
    reason = "target matches declared allowlist" if decision == "ALLOWED" else "target is outside declared allowlist"
    return {"index": index, "source_line": source_line, **payload, "normalised_target": normalised, "decision": decision, "reason": reason}


def build_receipt(policy: dict[str, Any], policy_raw: bytes, events: list[dict[str, Any]], trace_raw: bytes) -> dict[str, Any]:
    findings = [classify_event(policy, event, index) for index, event in enumerate(events, start=1)]
    counts = {decision: sum(item["decision"] == decision for item in findings) for decision in DECISIONS}
    verdict = "RED" if counts["VIOLATION"] else "AMBER" if counts["UNKNOWN"] else "GREEN"
    body = {
        "schema": RECEIPT_SCHEMA,
        "tool_version": VERSION,
        "run_id": policy["run_id"],
        "declared_actor": policy["actor"],
        "verdict": verdict,
        "counts": {"events": len(findings), **counts},
        "inputs": {"policy_sha256": sha256_bytes(policy_raw), "trace_sha256": sha256_bytes(trace_raw)},
        "findings": findings,
        "limits": {"max_input_bytes": MAX_INPUT_BYTES, "max_events": MAX_EVENTS},
        "claims": {
            "passive_observation_only": True,
            "execution_prevented": False,
            "trace_completeness_verified": False,
            "semantic_intent_verified": False,
            "security_certified": False,
        },
    }
    return {**body, "canonical_sha256": sha256_bytes(canonical_bytes(body))}


def render_markdown(receipt: dict[str, Any]) -> bytes:
    counts = receipt["counts"]
    lines = [
        "<!-- SPDX-License-Identifier: Apache-2.0 -->",
        f"# Agent Trace Receipt — {receipt['run_id']}",
        "",
        f"**Verdict:** `{receipt['verdict']}`  ",
        f"**Declared actor:** `{receipt['declared_actor']}`  ",
        f"**Events:** {counts['events']} · allowed {counts['ALLOWED']} · violations {counts['VIOLATION']} · unknown {counts['UNKNOWN']}",
        "",
        "| # | Seq | Kind | Target | Decision | Reason |",
        "|---:|---:|---|---|---|---|",
    ]
    for item in receipt["findings"]:
        cells = [item.get("index"), item.get("seq"), item.get("kind"), item.get("target"), item["decision"], item["reason"]]
        escaped = [str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ") for value in cells]
        lines.append("| " + " | ".join(escaped) + " |")
    lines.extend([
        "",
        "## Bounded interpretation",
        "",
        "This receipt compares supplied events with a supplied allowlist. It does not prove that the trace is complete, prevent execution, infer intent, or certify security.",
        "",
        f"Receipt hash: `{receipt['canonical_sha256']}`",
        "",
    ])
    return "\n".join(lines).encode("utf-8")


def build_artifacts(policy_path: pathlib.Path, trace_path: pathlib.Path) -> dict[str, bytes]:
    policy, policy_raw = load_policy(policy_path)
    events, trace_raw = load_trace(trace_path)
    receipt = build_receipt(policy, policy_raw, events, trace_raw)
    receipt_bytes = canonical_bytes(receipt)
    markdown_bytes = render_markdown(receipt)
    manifest_body = {
        "schema": MANIFEST_SCHEMA,
        "files": {
            "agent-trace-receipt.json": sha256_bytes(receipt_bytes),
            "agent-trace-receipt.md": sha256_bytes(markdown_bytes),
        },
        "claims": {"file_integrity_only": True, "truth_certified": False, "identity_certified": False},
    }
    manifest = {**manifest_body, "canonical_sha256": sha256_bytes(canonical_bytes(manifest_body))}
    return {
        "agent-trace-receipt.json": receipt_bytes,
        "agent-trace-receipt.md": markdown_bytes,
        "manifest.json": canonical_bytes(manifest),
    }


def verify_run(run_dir: pathlib.Path) -> dict[str, Any]:
    expected_names = {"agent-trace-receipt.json", "agent-trace-receipt.md", "manifest.json"}
    if not run_dir.is_dir():
        raise TraceError("run directory does not exist")
    actual_names = {path.name for path in run_dir.iterdir() if path.is_file()}
    if actual_names != expected_names:
        raise TraceError(f"run files differ; missing={sorted(expected_names-actual_names)}, extra={sorted(actual_names-expected_names)}")
    receipt_raw = _read_bounded(run_dir / "agent-trace-receipt.json")
    markdown_raw = _read_bounded(run_dir / "agent-trace-receipt.md")
    manifest_raw = _read_bounded(run_dir / "manifest.json")
    receipt = _decode_json(receipt_raw, "receipt")
    manifest = _decode_json(manifest_raw, "manifest")
    if not isinstance(receipt, dict) or not isinstance(manifest, dict):
        raise TraceError("receipt and manifest must be objects")
    if receipt.get("schema") != RECEIPT_SCHEMA or manifest.get("schema") != MANIFEST_SCHEMA:
        raise TraceError("receipt or manifest schema mismatch")
    receipt_body = dict(receipt)
    observed_receipt_hash = receipt_body.pop("canonical_sha256", None)
    if not isinstance(observed_receipt_hash, str) or not HEX64.fullmatch(observed_receipt_hash):
        raise TraceError("receipt canonical hash is missing or malformed")
    if observed_receipt_hash != sha256_bytes(canonical_bytes(receipt_body)):
        raise TraceError("receipt canonical hash mismatch")
    invariant_claims = receipt.get("claims")
    expected_claims = {
        "passive_observation_only": True,
        "execution_prevented": False,
        "trace_completeness_verified": False,
        "semantic_intent_verified": False,
        "security_certified": False,
    }
    if invariant_claims != expected_claims:
        raise TraceError("receipt bounded-claim invariant mismatch")
    if receipt.get("verdict") not in {"GREEN", "AMBER", "RED"}:
        raise TraceError("receipt verdict invariant mismatch")
    manifest_body = dict(manifest)
    observed_manifest_hash = manifest_body.pop("canonical_sha256", None)
    if observed_manifest_hash != sha256_bytes(canonical_bytes(manifest_body)):
        raise TraceError("manifest canonical hash mismatch")
    expected_hashes = {
        "agent-trace-receipt.json": sha256_bytes(receipt_raw),
        "agent-trace-receipt.md": sha256_bytes(markdown_raw),
    }
    if manifest.get("files") != expected_hashes:
        raise TraceError("artifact hash mismatch")
    return receipt


def replay(policy_path: pathlib.Path, trace_path: pathlib.Path, run_dir: pathlib.Path) -> None:
    expected = build_artifacts(policy_path, trace_path)
    for name, content in expected.items():
        path = run_dir / name
        if not path.is_file() or path.read_bytes() != content:
            raise TraceError(f"replay differs: {name}")
