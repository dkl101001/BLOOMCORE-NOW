# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Deterministic pledge scaffolding, audit, version diff, and receipts."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Iterable

PACKET_SCHEMA = "BLOOMCORE_NOW.PLEDGE_PACKET.v1"
AUDIT_SCHEMA = "BLOOMCORE_NOW.PLEDGE_AUDIT_RECEIPT.v1"
DIFF_SCHEMA = "BLOOMCORE_NOW.PLEDGE_DIFF_RECEIPT.v1"
TOOL_VERSION = "0.1.0"

CORE_FIELDS = ("actor", "action", "scope", "trigger", "evidence")
ACCOUNTABILITY_FIELDS = ("deadline_or_cadence", "consequence")
ALL_AUDIT_FIELDS = CORE_FIELDS + ACCOUNTABILITY_FIELDS + ("exceptions",)
LIFECYCLES = {"active", "proposed", "withdrawn", "superseded"}
MODAL = re.compile(r"\b(must|should|shall|will|commits?\s+to|pledges?\s+to)\b", re.I)
LIST_PREFIX = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _receipt(payload: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    result["receipt_id"] = "sha256:" + hashlib.sha256(_canonical(result)).hexdigest()
    return result


def _load_json(raw: bytes) -> Any:
    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid UTF-8 JSON: {exc}") from exc


def inspect_json_bytes(raw: bytes) -> dict[str, Any]:
    """Parse a pledge packet while rejecting ambiguous JSON."""
    value = _load_json(raw)
    if not isinstance(value, dict):
        raise ValueError("pledge packet root must be an object")
    return value


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _known(value: Any) -> bool:
    """Empty exceptions is explicit knowledge; other empty containers are absent."""
    return value == [] or _present(value)


def _validate_packet(packet: dict[str, Any]) -> None:
    if packet.get("schema") != PACKET_SCHEMA:
        raise ValueError(f"schema must be {PACKET_SCHEMA}")
    document = packet.get("document")
    if not isinstance(document, dict):
        raise ValueError("document must be an object")
    for key in ("title", "issuer", "version", "source_url", "source_sha256"):
        if not isinstance(document.get(key), str) or not document[key].strip():
            raise ValueError(f"document.{key} must be a non-empty string")
    if not HEX64.fullmatch(document["source_sha256"]):
        raise ValueError("document.source_sha256 must be 64 lowercase hexadecimal characters")
    commitments = packet.get("commitments")
    if not isinstance(commitments, list) or not commitments:
        raise ValueError("commitments must be a non-empty array")
    seen: set[str] = set()
    for index, commitment in enumerate(commitments):
        if not isinstance(commitment, dict):
            raise ValueError(f"commitments[{index}] must be an object")
        identifier = commitment.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError(f"commitments[{index}].id must be a non-empty string")
        if identifier in seen:
            raise ValueError(f"duplicate commitment id: {identifier}")
        seen.add(identifier)
        if not isinstance(commitment.get("text"), str) or not commitment["text"].strip():
            raise ValueError(f"commitment {identifier}.text must be a non-empty string")
        lifecycle = commitment.get("lifecycle", "proposed")
        if lifecycle not in LIFECYCLES:
            raise ValueError(f"commitment {identifier}.lifecycle must be one of {sorted(LIFECYCLES)}")
        evidence = commitment.get("evidence")
        if evidence is not None and (
            not isinstance(evidence, list)
            or any(not isinstance(item, str) or not item.strip() for item in evidence)
        ):
            raise ValueError(f"commitment {identifier}.evidence must be null or an array of strings")
        exceptions = commitment.get("exceptions")
        if exceptions is not None and (
            not isinstance(exceptions, list)
            or any(not isinstance(item, str) or not item.strip() for item in exceptions)
        ):
            raise ValueError(f"commitment {identifier}.exceptions must be null or an array of strings")


def _field_state(field: str, value: Any) -> str:
    if field == "exceptions" and value == []:
        return "explicit_none"
    return "present" if _present(value) else "unknown"


def _finding(commitment: dict[str, Any]) -> dict[str, Any]:
    lifecycle = commitment.get("lifecycle", "proposed")
    states = {field: _field_state(field, commitment.get(field)) for field in ALL_AUDIT_FIELDS}
    core_count = sum(_known(commitment.get(field)) for field in CORE_FIELDS)
    accountability_count = sum(
        _known(commitment.get(field)) for field in ACCOUNTABILITY_FIELDS
    )
    exceptions_known = _known(commitment.get("exceptions"))
    if lifecycle in {"withdrawn", "superseded"}:
        auditability = lifecycle
    elif core_count == len(CORE_FIELDS) and accountability_count >= 1 and exceptions_known:
        auditability = "testable"
    elif _known(commitment.get("actor")) and _known(commitment.get("action")) and core_count >= 3:
        auditability = "partial"
    else:
        auditability = "declarative"
    missing = [field for field, state in states.items() if state == "unknown"]
    return {
        "id": commitment["id"],
        "text": commitment["text"],
        "lifecycle": lifecycle,
        "source_locator": commitment.get("source_locator"),
        "auditability": auditability,
        "field_states": states,
        "missing_fields": missing,
        "claim_boundary": "structural-field-presence-only",
    }


def audit_packet(packet: dict[str, Any], source_bytes: bytes | None = None) -> dict[str, Any]:
    """Create a structural audit receipt; no policy meaning or compliance is certified."""
    _validate_packet(packet)
    expected = packet["document"]["source_sha256"]
    observed = hashlib.sha256(source_bytes).hexdigest() if source_bytes is not None else None
    if observed is not None and observed != expected:
        raise ValueError("source SHA-256 does not match document.source_sha256")
    findings = [_finding(item) for item in packet["commitments"]]
    counts = {key: 0 for key in ("testable", "partial", "declarative", "withdrawn", "superseded")}
    for finding in findings:
        counts[finding["auditability"]] += 1
    active_gaps = counts["partial"] + counts["declarative"]
    payload = {
        "schema": AUDIT_SCHEMA,
        "tool": {"name": "bloomcore-pledge-receipt", "version": TOOL_VERSION},
        "document": copy.deepcopy(packet["document"]),
        "source_verification": {
            "performed": source_bytes is not None,
            "expected_sha256": expected,
            "observed_sha256": observed,
            "matched": observed == expected if observed is not None else None,
        },
        "summary": {
            **counts,
            "commitment_count": len(findings),
            "active_structural_gaps": active_gaps,
            "all_active_commitments_testable": active_gaps == 0,
        },
        "findings": findings,
        "limitations": [
            "Field presence does not establish policy quality, semantic correctness, implementation, compliance, or real-world behavior.",
            "Operator-supplied annotations remain assertions unless backed by separately inspected evidence.",
            "The tool does not decide whose values, authority model, or governance philosophy is correct.",
            "A receipt witnesses only deterministic structure and optional source-byte correspondence.",
        ],
        "authority": "observational",
        "release_state": "Phi — RELEASE_CANDIDATE_NOT_SHIPPED",
    }
    return _receipt(payload)


def _candidate_lines(markdown: str) -> Iterable[tuple[int, str]]:
    paragraph: list[str] = []
    start = 0
    for number, raw in enumerate(markdown.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            if paragraph:
                yield start, " ".join(paragraph)
                paragraph = []
            continue
        if LIST_PREFIX.match(raw):
            if paragraph:
                yield start, " ".join(paragraph)
                paragraph = []
            yield number, LIST_PREFIX.sub("", stripped).strip()
        else:
            if not paragraph:
                start = number
            paragraph.append(stripped)
    if paragraph:
        yield start, " ".join(paragraph)


def scaffold_markdown(
    raw: bytes,
    *,
    title: str,
    issuer: str,
    version: str,
    source_url: str,
    published: str | None = None,
) -> dict[str, Any]:
    """Extract candidate normative statements without inferring their structure."""
    try:
        markdown = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"source must be UTF-8: {exc}") from exc
    commitments: list[dict[str, Any]] = []
    for line, text in _candidate_lines(markdown):
        if not MODAL.search(text):
            continue
        normalized = " ".join(text.split())
        identifier = "pledge-" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
        commitments.append({
            "id": identifier,
            "text": normalized,
            "lifecycle": "proposed",
            "source_locator": f"line:{line}",
            "actor": None,
            "action": None,
            "scope": None,
            "trigger": None,
            "evidence": None,
            "deadline_or_cadence": None,
            "exceptions": None,
            "consequence": None,
        })
    if not commitments:
        raise ValueError("no candidate pledge statements found")
    return {
        "$comment": "SPDX-License-Identifier: Apache-2.0",
        "schema": PACKET_SCHEMA,
        "document": {
            "title": title,
            "issuer": issuer,
            "version": version,
            "published": published,
            "source_url": source_url,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
        },
        "commitments": commitments,
        "scaffold_boundary": "candidate extraction only; fields are intentionally unknown until a human annotates them",
    }


def _indexed(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    _validate_packet(packet)
    return {item["id"]: item for item in packet["commitments"]}


def diff_packets(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compare two structured versions by stable commitment ID."""
    old = _indexed(before)
    new = _indexed(after)
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changes: list[dict[str, Any]] = []
    weakened = 0
    for identifier in sorted(set(old) & set(new)):
        item_changes: list[dict[str, Any]] = []
        for field in ("text", "lifecycle", "source_locator") + ALL_AUDIT_FIELDS:
            left, right = old[identifier].get(field), new[identifier].get(field)
            if left == right:
                continue
            if _known(left) and not _known(right):
                kind = "field_lost"
                weakened += 1
            elif not _known(left) and _known(right):
                kind = "field_gained"
            else:
                kind = "field_changed"
            item_changes.append({"field": field, "kind": kind, "before": left, "after": right})
        if item_changes:
            changes.append({"id": identifier, "changes": item_changes})
    weakened += len(removed)
    payload = {
        "schema": DIFF_SCHEMA,
        "tool": {"name": "bloomcore-pledge-receipt", "version": TOOL_VERSION},
        "before": copy.deepcopy(before["document"]),
        "after": copy.deepcopy(after["document"]),
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changes),
            "structural_weakening_signals": weakened,
        },
        "added_ids": added,
        "removed_ids": removed,
        "changed_commitments": changes,
        "limitations": [
            "A structural change is not automatically a substantive weakening or improvement.",
            "Stable IDs and annotations are operator-supplied and must be reviewed against source text.",
            "This diff does not establish compliance, intent, implementation, or real-world conduct.",
        ],
        "authority": "observational",
        "release_state": "Phi — RELEASE_CANDIDATE_NOT_SHIPPED",
    }
    return _receipt(payload)


def verify_receipt(receipt: dict[str, Any]) -> bool:
    """Verify the deterministic self-hash without certifying the underlying claim."""
    if not isinstance(receipt, dict) or receipt.get("schema") not in {AUDIT_SCHEMA, DIFF_SCHEMA}:
        return False
    expected = receipt.get("receipt_id")
    if not isinstance(expected, str) or not expected.startswith("sha256:"):
        return False
    payload = copy.deepcopy(receipt)
    del payload["receipt_id"]
    return expected == "sha256:" + hashlib.sha256(_canonical(payload)).hexdigest()


def render_markdown(receipt: dict[str, Any]) -> str:
    """Render either audit or diff receipts as stable Markdown."""
    if receipt.get("schema") == AUDIT_SCHEMA:
        summary = receipt["summary"]
        lines = [
            "<!-- SPDX-License-Identifier: Apache-2.0 -->",
            "",
            "# BLOOMCORE Pledge Receipt",
            "",
            f"Receipt: `{receipt['receipt_id']}`",
            f"Document: **{receipt['document']['title']}** — {receipt['document']['issuer']} `{receipt['document']['version']}`",
            "",
            "| Testable | Partial | Declarative | Withdrawn | Superseded |",
            "|---:|---:|---:|---:|---:|",
            f"| {summary['testable']} | {summary['partial']} | {summary['declarative']} | {summary['withdrawn']} | {summary['superseded']} |",
            "",
            "## Commitments",
            "",
            "| ID | Lifecycle | Auditability | Missing structure |",
            "|---|---|---|---|",
        ]
        for item in receipt["findings"]:
            missing = ", ".join(item["missing_fields"]) or "—"
            lines.append(f"| `{item['id']}` | `{item['lifecycle']}` | `{item['auditability']}` | {missing} |")
    elif receipt.get("schema") == DIFF_SCHEMA:
        summary = receipt["summary"]
        lines = [
            "<!-- SPDX-License-Identifier: Apache-2.0 -->",
            "",
            "# BLOOMCORE Pledge Diff Receipt",
            "",
            f"Receipt: `{receipt['receipt_id']}`",
            f"Versions: `{receipt['before']['version']}` → `{receipt['after']['version']}`",
            "",
            "| Added | Removed | Changed | Structural weakening signals |",
            "|---:|---:|---:|---:|",
            f"| {summary['added']} | {summary['removed']} | {summary['changed']} | {summary['structural_weakening_signals']} |",
            "",
            "## Removed IDs",
            "",
        ]
        lines.extend(f"- `{item}`" for item in receipt["removed_ids"])
        if not receipt["removed_ids"]:
            lines.append("- None")
        lines.extend(["", "## Changed commitments", ""])
        if not receipt["changed_commitments"]:
            lines.append("- None")
        for item in receipt["changed_commitments"]:
            lines.append(f"- `{item['id']}`")
            lines.extend(f"  - `{change['field']}`: `{change['kind']}`" for change in item["changes"])
    else:
        raise ValueError("unsupported receipt schema")
    lines.extend(["", "## Boundary", ""])
    lines.extend(f"- {item}" for item in receipt["limitations"])
    lines.extend(["", f"Release state: `{receipt['release_state']}`", ""])
    return "\n".join(lines)
