# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Pure inspection and deterministic receipt rendering."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Callable, Iterable

TOOL_VERSION = "0.1.0"
SCHEMA = "BLOOMCORE_NOW.SBOM_RECEIPT.v1"
PROFILE_NAME = "CISA-2026-Minimum-Elements-Structural-Profile"
PROFILE_URL = (
    "https://media.defense.gov/2026/Jul/29/2003971159/-1/-1/1/"
    "CSI_2026_cisa_sbom_minimum_elements_508c.PDF"
)
UNKNOWN_MARKERS = {"unknown", "noassertion", "not known", "undetermined"}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _is_blank(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _flatten(values: Iterable[Any]) -> list[Any]:
    flat: list[Any] = []
    for value in values:
        if isinstance(value, (list, tuple)):
            flat.extend(_flatten(value))
        else:
            flat.append(value)
    return flat


def _status(*values: Any) -> str:
    candidates = [value for value in _flatten(values) if not _is_blank(value)]
    if not candidates:
        return "missing"
    known = [
        value
        for value in candidates
        if not (isinstance(value, str) and value.strip().lower() in UNKNOWN_MARKERS)
    ]
    return "present" if known else "explicit_unknown"


def _finding(
    element_id: str,
    label: str,
    status: str,
    path: str,
    note: str,
) -> dict[str, str]:
    return {
        "element_id": element_id,
        "label": label,
        "status": status,
        "path": path,
        "note": note,
    }


def _entity_values(entity: Any) -> list[Any]:
    if not isinstance(entity, dict):
        return [entity]
    return [entity.get("name"), entity.get("email"), entity.get("url")]


def _author_values(metadata: dict[str, Any]) -> list[Any]:
    values: list[Any] = []
    for author in metadata.get("authors", []) or []:
        values.extend(_entity_values(author))
    for key in ("manufacturer", "manufacture"):
        values.extend(_entity_values(metadata.get(key)))
    return values


def _tool_records(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    tools = metadata.get("tools")
    if isinstance(tools, list):
        return [tool for tool in tools if isinstance(tool, dict)]
    if not isinstance(tools, dict):
        return []
    records: list[dict[str, Any]] = []
    for key in ("components", "services"):
        records.extend(
            item for item in (tools.get(key) or []) if isinstance(item, dict)
        )
    return records


def _component_records(document: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    records: list[tuple[str, dict[str, Any]]] = []

    def walk(component: Any, path: str) -> None:
        if not isinstance(component, dict):
            return
        records.append((path, component))
        for index, child in enumerate(component.get("components", []) or []):
            walk(child, f"{path}.components[{index}]")

    root_component = (document.get("metadata") or {}).get("component")
    if root_component:
        walk(root_component, "$.metadata.component")
    for index, component in enumerate(document.get("components", []) or []):
        walk(component, f"$.components[{index}]")
    return records


def _producer_values(component: dict[str, Any]) -> list[Any]:
    values: list[Any] = []
    for key in ("supplier", "manufacturer"):
        values.extend(_entity_values(component.get(key)))
    for author in component.get("authors", []) or []:
        values.extend(_entity_values(author))
    values.extend([component.get("author"), component.get("publisher")])
    return values


def _identifier_values(component: dict[str, Any]) -> list[Any]:
    values: list[Any] = [component.get("purl"), component.get("cpe")]
    for key in ("omniborId", "swhid"):
        values.append(component.get(key))
    swid = component.get("swid")
    if isinstance(swid, dict):
        values.extend([swid.get("tagId"), swid.get("name")])
    return values


def _license_values(component: dict[str, Any]) -> list[Any]:
    values: list[Any] = []
    for choice in component.get("licenses", []) or []:
        if not isinstance(choice, dict):
            values.append(choice)
            continue
        values.append(choice.get("expression"))
        license_record = choice.get("license")
        if isinstance(license_record, dict):
            values.extend([license_record.get("id"), license_record.get("name")])
    return values


def _dependency_refs(document: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for relationship in document.get("dependencies", []) or []:
        if not isinstance(relationship, dict):
            continue
        ref = relationship.get("ref")
        if isinstance(ref, str) and ref:
            refs.add(ref)
    return refs


def _document_findings(document: dict[str, Any]) -> list[dict[str, str]]:
    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    tools = _tool_records(metadata)
    return [
        _finding("sbom_author", "SBOM author", _status(_author_values(metadata)), "$.metadata.authors|manufacturer", "CycloneDX authors or manufacturer identity."),
        _finding("sbom_author_signature", "SBOM author signature", _status(document.get("signature")), "$.signature", "Presence only; cryptographic validity is not verified."),
        _finding("timestamp", "Timestamp", _status(metadata.get("timestamp")), "$.metadata.timestamp", "Timestamp value is not independently verified."),
        _finding("data_format_name", "Data format name", _status(document.get("bomFormat")), "$.bomFormat", "Expected CycloneDX for this profile."),
        _finding("data_format_version", "Data format version", _status(document.get("specVersion")), "$.specVersion", "Supported structural mappings cover CycloneDX 1.4 through 1.7."),
        _finding("generation_context", "Generation context", _status(metadata.get("lifecycles")), "$.metadata.lifecycles", "CycloneDX lifecycle data is used as the bounded generation-context mapping."),
        _finding("tool_name", "Tool name", _status([tool.get("name") for tool in tools]), "$.metadata.tools[*].name", "At least one generator/tool name."),
        _finding("tool_version", "Tool version", _status([tool.get("version") for tool in tools]), "$.metadata.tools[*].version", "At least one generator/tool version."),
        _finding("sbom_version", "SBOM version", _status(document.get("version")), "$.version", "Document revision/version, not CycloneDX specification version."),
    ]


def _component_findings(
    path: str, component: dict[str, Any], dependency_refs: set[str]
) -> dict[str, Any]:
    hashes = [item for item in component.get("hashes", []) or [] if isinstance(item, dict)]
    ref = component.get("bom-ref")
    dependency_status = _status(ref) if ref in dependency_refs else "missing"
    label = component.get("name") or ref or path
    return {
        "component": label,
        "path": path,
        "bom_ref": ref,
        "findings": [
            _finding("component_name", "Component name", _status(component.get("name")), f"{path}.name", "Human-readable component name."),
            _finding("component_version", "Component version", _status(component.get("version")), f"{path}.version", "Component version string."),
            _finding("component_producer", "Component producer", _status(_producer_values(component)), f"{path}.supplier|manufacturer|authors", "Supplier, manufacturer, author or publisher identity."),
            _finding("component_identifier", "Component identifier", _status(_identifier_values(component)), f"{path}.purl|cpe|swid|omniborId|swhid", "External identifier; bom-ref alone is not counted."),
            _finding("component_hash_value", "Component hash value", _status([item.get("content") for item in hashes]), f"{path}.hashes[*].content", "Presence only; artifact correspondence is not verified."),
            _finding("component_hash_algorithm", "Component hash algorithm", _status([item.get("alg") for item in hashes]), f"{path}.hashes[*].alg", "Presence only; algorithm strength is not graded."),
            _finding("component_license", "Component license", _status(_license_values(component)), f"{path}.licenses", "License identifier, name or expression; legal meaning is not evaluated."),
            _finding("component_dependency_relationship", "Component dependency relationship", dependency_status, "$.dependencies[*].ref", "The component bom-ref appears as a dependency-graph node."),
        ],
    }


PROCESS_PRACTICES = (
    ("generation_frequency", "Generation frequency"),
    ("generation_depth", "Generation depth and coverage"),
    ("known_unknowns_process", "Known-unknowns process"),
    ("distribution_and_delivery", "Distribution and delivery"),
    ("access_control", "Access control"),
    ("accommodation_of_updates", "Accommodation of updates"),
)


def _summary(findings: Iterable[dict[str, Any]]) -> dict[str, Any]:
    counts = {"present": 0, "explicit_unknown": 0, "missing": 0, "not_machine_verifiable": 0}
    for finding in findings:
        counts[finding["status"]] += 1
    counts["structurally_complete"] = counts["missing"] == 0
    return counts


def inspect_document(document: dict[str, Any], source_sha256: str) -> dict[str, Any]:
    """Inspect a parsed CycloneDX JSON document and return a stable receipt."""
    if not isinstance(document, dict):
        raise ValueError("SBOM JSON root must be an object")
    if document.get("bomFormat") != "CycloneDX":
        raise ValueError("only CycloneDX JSON is supported")
    spec_version = str(document.get("specVersion", ""))
    if spec_version not in {"1.4", "1.5", "1.6", "1.7"}:
        raise ValueError("supported CycloneDX specVersion values are 1.4, 1.5, 1.6 and 1.7")

    document_findings = _document_findings(document)
    dependencies = _dependency_refs(document)
    component_findings = [
        _component_findings(path, component, dependencies)
        for path, component in _component_records(document)
    ]
    if not component_findings:
        document_findings.append(
            _finding("component_inventory", "Component inventory", "missing", "$.components|$.metadata.component", "No component records were found.")
        )
    practices = [
        _finding(element_id, label, "not_machine_verifiable", "$", "Requires organizational/process evidence outside one SBOM file.")
        for element_id, label in PROCESS_PRACTICES
    ]
    all_findings = document_findings + practices
    for component in component_findings:
        all_findings.extend(component["findings"])

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "tool": {"name": "bloomcore-sbom-receipt", "version": TOOL_VERSION},
        "profile": {
            "name": PROFILE_NAME,
            "published": "2026-07-29",
            "source": PROFILE_URL,
            "scope": "structural-presence-only",
        },
        "input": {
            "sha256": source_sha256,
            "bom_format": document.get("bomFormat"),
            "spec_version": spec_version,
            "component_count": len(component_findings),
        },
        "summary": _summary(all_findings),
        "document_findings": document_findings,
        "component_findings": component_findings,
        "process_practices": practices,
        "limitations": [
            "This receipt is not a legal, regulatory or procurement compliance determination.",
            "Presence does not prove accuracy, completeness, provenance, signature validity or artifact-hash correspondence.",
            "Process practices require evidence outside a single SBOM and are reported as not_machine_verifiable.",
            "The profile is a bounded implementation interpretation, not an official CISA conformance tool.",
        ],
        "authority": "observational",
        "release_state": "Phi — RELEASE_CANDIDATE_NOT_SHIPPED",
    }
    receipt["receipt_id"] = "sha256:" + hashlib.sha256(_canonical(receipt)).hexdigest()
    return receipt


def inspect_bytes(raw: bytes) -> dict[str, Any]:
    """Parse and inspect raw UTF-8 JSON bytes."""
    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")

    try:
        document = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid UTF-8 JSON: {exc}") from exc
    return inspect_document(document, hashlib.sha256(raw).hexdigest())


def verify_receipt(receipt: dict[str, Any]) -> bool:
    """Verify the receipt's self-hash without asserting source-file truth."""
    if not isinstance(receipt, dict):
        return False
    expected = receipt.get("receipt_id")
    if not isinstance(expected, str) or not expected.startswith("sha256:"):
        return False
    payload = copy.deepcopy(receipt)
    del payload["receipt_id"]
    actual = "sha256:" + hashlib.sha256(_canonical(payload)).hexdigest()
    return actual == expected


def render_markdown(receipt: dict[str, Any]) -> str:
    """Render a compact, deterministic human-readable receipt."""
    summary = receipt["summary"]
    lines = [
        "<!-- SPDX-License-Identifier: Apache-2.0 -->",
        "",
        "# BLOOMCORE SBOM Receipt",
        "",
        f"Receipt: `{receipt['receipt_id']}`",
        f"Input SHA-256: `{receipt['input']['sha256']}`",
        f"Profile: `{receipt['profile']['name']}`",
        "",
        "## Summary",
        "",
        "| Present | Explicit unknown | Missing | Not machine-verifiable | Structurally complete |",
        "|---:|---:|---:|---:|---|",
        f"| {summary['present']} | {summary['explicit_unknown']} | {summary['missing']} | {summary['not_machine_verifiable']} | {'yes' if summary['structurally_complete'] else 'no'} |",
        "",
        "## Document elements",
        "",
        "| Element | Status | Path |",
        "|---|---|---|",
    ]
    for finding in receipt["document_findings"]:
        lines.append(f"| {finding['label']} | `{finding['status']}` | `{finding['path']}` |")
    for component in receipt["component_findings"]:
        lines.extend(["", f"## Component — {component['component']}", "", "| Element | Status | Path |", "|---|---|---|"])
        for finding in component["findings"]:
            lines.append(f"| {finding['label']} | `{finding['status']}` | `{finding['path']}` |")
    lines.extend(["", "## Process practices", ""])
    for finding in receipt["process_practices"]:
        lines.append(f"- **{finding['label']}:** `not_machine_verifiable` — {finding['note']}")
    lines.extend(["", "## Boundary", ""])
    lines.extend(f"- {item}" for item in receipt["limitations"])
    lines.extend(["", f"Release state: `{receipt['release_state']}`", ""])
    return "\n".join(lines)
