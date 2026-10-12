# SPDX-License-Identifier: MPL-2.0
"""Deterministic structural evaluator for bounded RVP-01 receipts.

This validator checks evidence structure, local byte bindings, and declared
dependency closure. It cannot decide whether a semantic or scientific claim is
true and it has no execution, admission, governance, or publication authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "bloomcore.reconstruction-preflight/v0.1"
RECEIPT_SCHEMA = "bloomcore.reconstruction-preflight-receipt/v0.1"
TOOL_VERSION = "0.1.0"
DIMENSIONS = ("authority", "dependencies", "ancestry", "state", "behavior", "meaning")
CLOSING_STATUSES = {"VERIFIED", "NOT_APPLICABLE_WITH_EVIDENCE"}
ALLOWED_STATUSES = CLOSING_STATUSES | {"FAILED", "MISSING", "CONFLICTING", "UNKNOWN"}
DISPOSITIONS = {
    "VERIFIED_FOR_BUILD_SCOPE",
    "PARTIAL_BUT_INDEPENDENT_WORK_SAFE",
    "RECONSTRUCTION_BLOCKED",
}


class ManifestError(ValueError):
    """Raised when the input cannot be evaluated safely."""


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def digest_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def load_manifest(path: str | Path) -> tuple[dict[str, Any], Path, str]:
    manifest_path = Path(path).resolve()
    raw = manifest_path.read_bytes()
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ManifestError(f"duplicate JSON object key: {key}")
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"manifest is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ManifestError("manifest root must be an object")
    return value, manifest_path, digest_bytes(canonical_bytes(value))


def _nonempty_string(value: Any, label: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return ""
    return value.strip()


def _string_list(value: Any, label: str, errors: list[str], *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        errors.append(f"{label} must be {'a non-empty' if nonempty else 'an'} array")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{label}[{index}] must be a non-empty string")
        else:
            result.append(item.strip())
    return result


def _safe_relative_file(base: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ManifestError("source path must be relative to the manifest")
    resolved = (base / candidate).resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError as exc:
        raise ManifestError("source path escapes the manifest directory") from exc
    return resolved


@dataclass(frozen=True)
class Evaluation:
    disposition: str
    receipt: Mapping[str, Any]
    issues: tuple[Mapping[str, str], ...]

    def receipt_with_hash(self) -> dict[str, Any]:
        result = dict(self.receipt)
        result["receipt_hash"] = digest_bytes(canonical_bytes(self.receipt))
        return result


def evaluate_manifest(
    manifest: Mapping[str, Any], *, manifest_path: Path, input_sha256: str
) -> Evaluation:
    errors: list[str] = []
    findings: list[dict[str, str]] = []

    if manifest.get("schema") != SCHEMA:
        errors.append(f"schema must equal {SCHEMA!r}")
    scope = manifest.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
        scope = {}
    scope_id = _nonempty_string(scope.get("id"), "scope.id", errors)
    accepted_changes = _string_list(
        scope.get("accepted_changes"), "scope.accepted_changes", errors, nonempty=True
    )

    raw_dimensions = manifest.get("dimensions")
    if not isinstance(raw_dimensions, dict):
        errors.append("dimensions must be an object")
        raw_dimensions = {}
    normalized_dimensions: dict[str, Any] = {}
    unresolved_dimensions: set[str] = set()
    for name in DIMENSIONS:
        dimension = raw_dimensions.get(name)
        if not isinstance(dimension, dict):
            errors.append(f"dimensions.{name} must be an object")
            dimension = {}
        status = dimension.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"dimensions.{name}.status is invalid")
            status = "UNKNOWN"
        predicate = _nonempty_string(dimension.get("predicate"), f"dimensions.{name}.predicate", errors)
        observation = _nonempty_string(
            dimension.get("observation"), f"dimensions.{name}.observation", errors
        )
        evidence = _string_list(
            dimension.get("evidence"), f"dimensions.{name}.evidence", errors, nonempty=True
        )
        requirement_ids = _string_list(
            dimension.get("requirement_ids"), f"dimensions.{name}.requirement_ids", errors, nonempty=True
        )
        if status == "NOT_APPLICABLE_WITH_EVIDENCE" and len(evidence) < 1:
            errors.append(f"dimensions.{name} cannot be inapplicable without evidence")
        if status not in CLOSING_STATUSES:
            unresolved_dimensions.add(name)
            findings.append({"code": f"DIMENSION_{status}", "subject": name})
        normalized_dimensions[name] = {
            "evidence": sorted(evidence),
            "observation": observation,
            "predicate": predicate,
            "requirement_ids": sorted(requirement_ids),
            "status": status,
        }

    raw_sources = manifest.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        errors.append("sources must be a non-empty array")
        raw_sources = []
    source_ids: set[str] = set()
    verified_sources: set[str] = set()
    normalized_sources: list[dict[str, Any]] = []
    for index, source in enumerate(raw_sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label} must be an object")
            continue
        source_id = _nonempty_string(source.get("id"), f"{label}.id", errors)
        if source_id in source_ids:
            errors.append(f"duplicate source id: {source_id}")
        source_ids.add(source_id)
        expected = _nonempty_string(source.get("sha256"), f"{label}.sha256", errors).lower()
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            errors.append(f"{label}.sha256 must be 64 lowercase hexadecimal characters")
        required = source.get("required")
        if not isinstance(required, bool):
            errors.append(f"{label}.required must be boolean")
            required = True
        path_value = source.get("path")
        observed: str | None = None
        status = "REFERENCE_ONLY"
        if path_value is not None:
            if not isinstance(path_value, str) or not path_value:
                errors.append(f"{label}.path must be a non-empty string when present")
            else:
                try:
                    source_path = _safe_relative_file(manifest_path.parent, path_value)
                except ManifestError as exc:
                    errors.append(f"{label}.path: {exc}")
                else:
                    if not source_path.is_file():
                        status = "MISSING"
                        findings.append({"code": "SOURCE_MISSING", "subject": source_id})
                    else:
                        observed = digest_bytes(source_path.read_bytes())
                        if observed == expected:
                            status = "VERIFIED"
                            verified_sources.add(source_id)
                        else:
                            status = "HASH_MISMATCH"
                            findings.append({"code": "SOURCE_HASH_MISMATCH", "subject": source_id})
        elif required:
            status = "UNRETRIEVED_REQUIRED"
            findings.append({"code": "SOURCE_UNRETRIEVED", "subject": source_id})
        else:
            verified_sources.add(source_id)
        normalized_sources.append(
            {
                "id": source_id,
                "observed_sha256": observed,
                "required": required,
                "sha256": expected,
                "status": status,
            }
        )

    raw_independent = scope.get("independent_work", [])
    if not isinstance(raw_independent, list):
        errors.append("scope.independent_work must be an array")
        raw_independent = []
    safe_independent: list[str] = []
    unsafe_independent: list[str] = []
    normalized_independent: list[dict[str, Any]] = []
    for index, item in enumerate(raw_independent):
        label = f"scope.independent_work[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        item_id = _nonempty_string(item.get("id"), f"{label}.id", errors)
        dependency_ids = _string_list(
            item.get("dependency_ids"), f"{label}.dependency_ids", errors, nonempty=True
        )
        dimension_ids = _string_list(
            item.get("dimension_ids"), f"{label}.dimension_ids", errors, nonempty=True
        )
        requirement_ids = _string_list(
            item.get("requirement_ids"), f"{label}.requirement_ids", errors, nonempty=True
        )
        unknown_dimensions = sorted(set(dimension_ids) - set(DIMENSIONS))
        unknown_dependencies = sorted(set(dependency_ids) - source_ids)
        open_dimensions = sorted(
            name for name in dimension_ids if name in DIMENSIONS and name in unresolved_dimensions
        )
        open_dependencies = sorted(set(dependency_ids) - verified_sources)
        safe = not (unknown_dimensions or unknown_dependencies or open_dimensions or open_dependencies)
        (safe_independent if safe else unsafe_independent).append(item_id)
        if not safe:
            findings.append({"code": "INDEPENDENCE_NOT_ESTABLISHED", "subject": item_id})
        normalized_independent.append(
            {
                "dependency_ids": sorted(dependency_ids),
                "dimension_ids": sorted(dimension_ids),
                "id": item_id,
                "requirement_ids": sorted(requirement_ids),
                "safe": safe,
            }
        )

    held_work = _string_list(scope.get("held_work", []), "scope.held_work", errors)
    if errors:
        raise ManifestError("; ".join(errors))

    source_blockers = any(
        item["required"] and item["status"] != "VERIFIED" for item in normalized_sources
    )
    has_blockers = bool(unresolved_dimensions or source_blockers)
    if not has_blockers:
        disposition = "VERIFIED_FOR_BUILD_SCOPE"
    elif safe_independent and not unsafe_independent and held_work:
        disposition = "PARTIAL_BUT_INDEPENDENT_WORK_SAFE"
    else:
        disposition = "RECONSTRUCTION_BLOCKED"
    assert disposition in DISPOSITIONS

    body: dict[str, Any] = {
        "accepted_changes": sorted(accepted_changes),
        "dimensions": normalized_dimensions,
        "disposition": disposition,
        "evidence_boundary": (
            "Structural and byte-binding checks only; this receipt does not certify truth, meaning, "
            "identity, scientific validity, admission, governance, or publication readiness."
        ),
        "findings": sorted(findings, key=lambda item: (item["code"], item["subject"])),
        "held_work": sorted(held_work),
        "independent_work": sorted(normalized_independent, key=lambda item: item["id"]),
        "manifest_semantic_sha256": input_sha256,
        "spdx_license_identifier": "Apache-2.0",
        "receipt_schema": RECEIPT_SCHEMA,
        "scope_id": scope_id,
        "sources": sorted(normalized_sources, key=lambda item: item["id"]),
        "tool_version": TOOL_VERSION,
    }
    return Evaluation(disposition, body, tuple(body["findings"]))


def verify_receipt(value: Mapping[str, Any]) -> tuple[bool, str]:
    if not isinstance(value, dict):
        return False, "receipt root must be an object"
    claimed = value.get("receipt_hash")
    if not isinstance(claimed, str):
        return False, "receipt_hash is missing"
    body = dict(value)
    del body["receipt_hash"]
    observed = digest_bytes(canonical_bytes(body))
    if claimed != observed:
        return False, f"receipt hash mismatch: expected {claimed}, observed {observed}"
    if body.get("receipt_schema") != RECEIPT_SCHEMA:
        return False, "receipt schema is unsupported"
    if body.get("disposition") not in DISPOSITIONS:
        return False, "receipt disposition is invalid"
    return True, observed

