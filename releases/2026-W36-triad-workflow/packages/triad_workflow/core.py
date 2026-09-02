# SPDX-License-Identifier: MPL-2.0
"""Strict validation and deterministic artifact construction."""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any

SCHEMA = "BLOOMCORE_NOW.TRIAD_WORKFLOW_PACKET.v1"
RECEIPT_SCHEMA = "BLOOMCORE_NOW.TRIAD_WORKFLOW_RECEIPT.v1"
MANIFEST_SCHEMA = "BLOOMCORE_NOW.TRIAD_SOURCE_MANIFEST.v1"

ROLE_RULES = {
    "SOLE_GOVERNING_MASTER": "GOVERNS",
    "BOUNDED_DSK_RESEARCH_COMPANION": "INFORMS_ONLY_WITHIN_SELECTED_APERTURE",
    "NON_AUTHORITATIVE_DISCOVERY_AND_EXECUTION_ADAPTER": "DISCOVERY_AND_EXECUTION_ONLY",
}
APERTURE = "PHASE38_SECTION_33_17_DYNAMIC_SCHRODINGER_KERNELS"
ROUTES = {"AUTHORITY_STATUS", "SOURCE_INTAKE", "IMPLEMENTATION_PROPOSAL", "RESEARCH_APERTURE"}
CLAIM_CLASSES = {
    "OBSERVED_DOCUMENTED",
    "RECONSTRUCTED_HISTORICAL_MEANING",
    "TECHNICAL_INTERPRETATION",
    "RESEARCH_HYPOTHESIS",
    "UNRESOLVED_ONTOLOGY",
}
AXES = (
    "transition",
    "recursion",
    "exploration",
    "scheduling",
    "replay",
    "persistence",
    "mutation",
    "authority",
)
PERMISSIONS = ("source_mutation", "native_mutation", "canonical_promotion", "external_action")
REQUIREMENT_STATES = {"OPEN", "BLOCKED", "CLOSED_WITH_EVIDENCE"}
ALLOWED_CLAIM = "BOUNDED_WORKFLOW_PACKET_VERIFIED"
CLAIMS_NOT_OBSERVED = (
    "SEMANTIC_TRUTH",
    "NATIVE_MANTIS_EXECUTION",
    "NATIVE_MIRRORSEED_METABOLISM",
    "NATIVE_STATE_MUTATION",
    "CANONICAL_PROMOTION",
    "SCIENTIFIC_VALIDATION",
    "FULL_PHASE151_EMBODIMENT",
    "ORGANISM_WIDE_REACHABILITY",
)


class WorkflowError(ValueError):
    """A bounded, user-correctable workflow validation failure."""


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise WorkflowError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise WorkflowError(f"non-finite JSON number is forbidden: {value}")

    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(str(exc)) from exc
    if not isinstance(value, dict):
        raise WorkflowError("workflow packet must be a JSON object")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise WorkflowError(f"{label} keys differ; missing={missing}, extra={extra}")


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowError(f"{label} must be a non-empty string")
    return value


def _safe_source(base_dir: pathlib.Path, relative: str) -> pathlib.Path:
    candidate = pathlib.Path(relative)
    if candidate.is_absolute():
        raise WorkflowError(f"source path must be relative: {relative}")
    base = base_dir.resolve()
    resolved = (base / candidate).resolve()
    if not resolved.is_relative_to(base) or resolved == base:
        raise WorkflowError(f"source path escapes packet directory: {relative}")
    if not resolved.is_file():
        raise WorkflowError(f"source file is missing: {relative}")
    return resolved


def validate_packet(packet: dict[str, Any], base_dir: pathlib.Path) -> dict[str, Any]:
    expected_top = {
        "$comment",
        "schema", "task_id", "goal", "mode", "route_id", "triad", "selected_aperture",
        "sources", "epistemic_claims", "execution_profile", "contradictions", "requirements",
        "requested_claim", "permissions",
    }
    _exact_keys(packet, expected_top, "packet")
    if packet["schema"] != SCHEMA:
        raise WorkflowError(f"schema must be {SCHEMA}")
    _nonempty_string(packet["task_id"], "task_id")
    _nonempty_string(packet["goal"], "goal")
    if packet["mode"] not in {"SAFE", "STRICT", "EXPLORATORY"}:
        raise WorkflowError("mode must be SAFE, STRICT, or EXPLORATORY")
    if packet["route_id"] not in ROUTES:
        raise WorkflowError(f"unknown route_id: {packet['route_id']}")

    triad = packet["triad"]
    if not isinstance(triad, dict):
        raise WorkflowError("triad must be an object")
    _exact_keys(triad, {"roles"}, "triad")
    roles = triad["roles"]
    if not isinstance(roles, list) or len(roles) != 3:
        raise WorkflowError("triad must contain exactly three differentiated roles")
    seen_roles: set[str] = set()
    seen_source_ids: set[str] = set()
    for index, role in enumerate(roles):
        if not isinstance(role, dict):
            raise WorkflowError(f"triad.roles[{index}] must be an object")
        _exact_keys(role, {"role", "source_id", "sha256", "authority"}, f"triad.roles[{index}]")
        role_name = role["role"]
        if role_name not in ROLE_RULES or role_name in seen_roles:
            raise WorkflowError(f"invalid or duplicate Triad role: {role_name}")
        if role["authority"] != ROLE_RULES[role_name]:
            raise WorkflowError(f"authority mismatch for {role_name}")
        source_id = _nonempty_string(role["source_id"], f"triad.roles[{index}].source_id")
        digest = role["sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise WorkflowError(f"invalid lowercase sha256 for {source_id}")
        if source_id in seen_source_ids:
            raise WorkflowError(f"duplicate role source_id: {source_id}")
        seen_roles.add(role_name)
        seen_source_ids.add(source_id)
    if seen_roles != set(ROLE_RULES):
        raise WorkflowError("all three named Triad roles are required")

    selected = packet["selected_aperture"]
    if selected not in {None, APERTURE}:
        raise WorkflowError("Keystone may be selected only for its exact DSK aperture")
    if packet["route_id"] == "RESEARCH_APERTURE" and selected != APERTURE:
        raise WorkflowError("RESEARCH_APERTURE route requires the exact DSK aperture")

    sources = packet["sources"]
    if not isinstance(sources, list) or len(sources) != 3:
        raise WorkflowError("sources must contain exactly the three role-bound sources")
    source_records: dict[str, dict[str, str]] = {}
    role_by_source = {role["source_id"]: role for role in roles}
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise WorkflowError(f"sources[{index}] must be an object")
        _exact_keys(source, {"source_id", "path", "sha256", "custody"}, f"sources[{index}]")
        source_id = source["source_id"]
        if source_id not in role_by_source or source_id in source_records:
            raise WorkflowError(f"unbound or duplicate source_id: {source_id}")
        if source["sha256"] != role_by_source[source_id]["sha256"]:
            raise WorkflowError(f"role/source hash mismatch for {source_id}")
        if source["custody"] not in {"PRIVATE_REFERENCE", "PUBLIC_SYNTHETIC_FIXTURE"}:
            raise WorkflowError(f"invalid custody for {source_id}")
        relative = _nonempty_string(source["path"], f"sources[{index}].path")
        resolved = _safe_source(base_dir, relative)
        observed = sha256_bytes(resolved.read_bytes())
        if observed != source["sha256"]:
            raise WorkflowError(f"source hash mismatch for {source_id}: expected {source['sha256']}, observed {observed}")
        source_records[source_id] = {
            "path": relative,
            "sha256": observed,
            "custody": source["custody"],
            "role": role_by_source[source_id]["role"],
        }
    if set(source_records) != seen_source_ids:
        raise WorkflowError("every Triad role must bind exactly one source")

    claims = packet["epistemic_claims"]
    if not isinstance(claims, list) or not claims:
        raise WorkflowError("epistemic_claims must be a non-empty list")
    observed_classes: set[str] = set()
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            raise WorkflowError(f"epistemic_claims[{index}] must be an object")
        _exact_keys(claim, {"claim_id", "class", "statement", "source_refs"}, f"epistemic_claims[{index}]")
        _nonempty_string(claim["claim_id"], f"epistemic_claims[{index}].claim_id")
        _nonempty_string(claim["statement"], f"epistemic_claims[{index}].statement")
        if claim["class"] not in CLAIM_CLASSES:
            raise WorkflowError(f"invalid epistemic class: {claim['class']}")
        refs = claim["source_refs"]
        if not isinstance(refs, list) or not refs or any(ref not in source_records for ref in refs):
            raise WorkflowError(f"claim {claim['claim_id']} has invalid source_refs")
        observed_classes.add(claim["class"])
    if observed_classes != CLAIM_CLASSES:
        raise WorkflowError("the packet must explicitly exercise all five epistemic claim classes")

    profile = packet["execution_profile"]
    if not isinstance(profile, dict):
        raise WorkflowError("execution_profile must be an object")
    _exact_keys(profile, set(AXES), "execution_profile")
    for axis in AXES:
        values = profile[axis]
        if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v.strip() for v in values):
            raise WorkflowError(f"execution axis {axis} must be a non-empty string list")

    contradictions = packet["contradictions"]
    if not isinstance(contradictions, list) or not contradictions:
        raise WorkflowError("at least one explicit contradiction/remainder record is required")
    for index, contradiction in enumerate(contradictions):
        if not isinstance(contradiction, dict):
            raise WorkflowError(f"contradictions[{index}] must be an object")
        _exact_keys(
            contradiction,
            {"contradiction_id", "source_refs", "pre_transform", "rejected_interpretations", "unresolved_remainder"},
            f"contradictions[{index}]",
        )
        _nonempty_string(contradiction["contradiction_id"], f"contradictions[{index}].contradiction_id")
        _nonempty_string(contradiction["pre_transform"], f"contradictions[{index}].pre_transform")
        _nonempty_string(contradiction["unresolved_remainder"], f"contradictions[{index}].unresolved_remainder")
        refs = contradiction["source_refs"]
        rejected = contradiction["rejected_interpretations"]
        if not isinstance(refs, list) or not refs or any(ref not in source_records for ref in refs):
            raise WorkflowError("contradiction source_refs must be non-empty and source-bound")
        if not isinstance(rejected, list) or not rejected or any(not isinstance(v, str) or not v.strip() for v in rejected):
            raise WorkflowError("rejected_interpretations must preserve at least one rejected reading")

    requirements = packet["requirements"]
    if not isinstance(requirements, list) or not requirements:
        raise WorkflowError("requirements must be a non-empty list")
    requirement_ids: set[str] = set()
    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, dict):
            raise WorkflowError(f"requirements[{index}] must be an object")
        _exact_keys(requirement, {"id", "criterion", "state", "evidence"}, f"requirements[{index}]")
        req_id = _nonempty_string(requirement["id"], f"requirements[{index}].id")
        _nonempty_string(requirement["criterion"], f"requirements[{index}].criterion")
        if req_id in requirement_ids:
            raise WorkflowError(f"duplicate requirement id: {req_id}")
        requirement_ids.add(req_id)
        if requirement["state"] not in REQUIREMENT_STATES:
            raise WorkflowError(f"requirement {req_id} has invalid state")
        evidence = requirement["evidence"]
        if not isinstance(evidence, list) or any(not isinstance(v, str) or not v.strip() for v in evidence):
            raise WorkflowError(f"requirement {req_id} evidence must be a string list")
        if requirement["state"] == "CLOSED_WITH_EVIDENCE" and not evidence:
            raise WorkflowError(f"requirement {req_id} is closed without evidence")
        if requirement["state"] != "CLOSED_WITH_EVIDENCE" and evidence:
            raise WorkflowError(f"requirement {req_id} has evidence but is not closed")

    permissions = packet["permissions"]
    if not isinstance(permissions, dict):
        raise WorkflowError("permissions must be an object")
    _exact_keys(permissions, set(PERMISSIONS), "permissions")
    if any(permissions[name] is not False for name in PERMISSIONS):
        raise WorkflowError("all mutation, promotion, and external-action permissions must be false")

    if any(req["state"] != "CLOSED_WITH_EVIDENCE" for req in requirements):
        raise WorkflowError("a verified packet requires every requirement CLOSED_WITH_EVIDENCE")
    if packet["requested_claim"] != ALLOWED_CLAIM:
        raise WorkflowError(f"requested_claim exceeds or differs from the bounded claim {ALLOWED_CLAIM}")

    return {"sources": source_records, "requirements": requirements}


def render_report(packet: dict[str, Any]) -> bytes:
    lines = [
        "<!-- SPDX-License-Identifier: Apache-2.0 -->",
        f"# Triad workflow report: {packet['task_id']}",
        "",
        f"**State:** Φ — RELEASE_CANDIDATE_NOT_SHIPPED  ",
        f"**Bounded claim:** `{ALLOWED_CLAIM}`  ",
        f"**Mode / route:** `{packet['mode']}` / `{packet['route_id']}`",
        "",
        "## Goal",
        "",
        packet["goal"],
        "",
        "## Differentiated authority",
        "",
        "| Role | Source | Authority |",
        "|---|---|---|",
    ]
    for role in packet["triad"]["roles"]:
        lines.append(f"| `{role['role']}` | `{role['source_id']}` | `{role['authority']}` |")
    lines.extend(["", "## Execution profile", ""])
    for axis in AXES:
        lines.append(f"- **{axis}:** " + "; ".join(packet["execution_profile"][axis]))
    lines.extend(["", "## Epistemic claims", ""])
    for claim in packet["epistemic_claims"]:
        lines.append(f"- `{claim['class']}` — {claim['statement']} ({', '.join(claim['source_refs'])})")
    lines.extend(["", "## Preserved contradiction and remainder", ""])
    for item in packet["contradictions"]:
        lines.append(f"- **{item['contradiction_id']}:** {item['pre_transform']}")
        lines.append(f"  - Rejected: {'; '.join(item['rejected_interpretations'])}")
        lines.append(f"  - Unresolved: {item['unresolved_remainder']}")
    lines.extend(["", "## Requirement evidence", ""])
    for req in packet["requirements"]:
        lines.append(f"- `{req['id']}` `{req['state']}` — {req['criterion']} — evidence: {'; '.join(req['evidence'])}")
    lines.extend(["", "## Claims not observed", ""])
    lines.extend(f"- `{claim}`" for claim in CLAIMS_NOT_OBSERVED)
    lines.extend(["", "This report is a deterministic structural witness, not a native MANTIS or MIRRORSEED result.", ""])
    return "\n".join(lines).encode("utf-8")


def build_artifacts(packet: dict[str, Any], base_dir: pathlib.Path) -> dict[str, bytes]:
    validated = validate_packet(packet, base_dir)
    input_bytes = canonical_bytes(packet)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "task_id": packet["task_id"],
        "input_sha256": sha256_bytes(input_bytes),
        "sources": [
            {"source_id": source_id, **validated["sources"][source_id]}
            for source_id in sorted(validated["sources"])
        ],
    }
    report_bytes = render_report(packet)
    manifest_bytes = canonical_bytes(manifest)
    receipt_body = {
        "schema": RECEIPT_SCHEMA,
        "task_id": packet["task_id"],
        "state": "PHI_RELEASE_CANDIDATE_NOT_SHIPPED",
        "bounded_claim": ALLOWED_CLAIM,
        "input_sha256": sha256_bytes(input_bytes),
        "source_manifest_sha256": sha256_bytes(manifest_bytes),
        "report_sha256": sha256_bytes(report_bytes),
        "execution_axes": list(AXES),
        "requirements": [
            {"id": req["id"], "state": req["state"], "evidence": req["evidence"]}
            for req in validated["requirements"]
        ],
        "claims_not_observed": list(CLAIMS_NOT_OBSERVED),
    }
    receipt = {**receipt_body, "canonical_sha256": sha256_bytes(canonical_bytes(receipt_body))}
    return {
        "TRIAD_REPORT.md": report_bytes,
        "source-manifest.json": manifest_bytes,
        "workflow-receipt.json": canonical_bytes(receipt),
    }


def verify_run(run_dir: pathlib.Path) -> None:
    receipt_path = run_dir / "workflow-receipt.json"
    receipt = load_json(receipt_path)
    expected_keys = {
        "schema", "task_id", "state", "bounded_claim", "input_sha256", "source_manifest_sha256",
        "report_sha256", "execution_axes", "requirements", "claims_not_observed", "canonical_sha256",
    }
    _exact_keys(receipt, expected_keys, "receipt")
    claimed = receipt.pop("canonical_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise WorkflowError("receipt canonical_sha256 is malformed")
    observed = sha256_bytes(canonical_bytes(receipt))
    if claimed != observed:
        raise WorkflowError(f"receipt canonical hash mismatch: expected {claimed}, observed {observed}")
    invariant_values = {
        "schema": RECEIPT_SCHEMA,
        "state": "PHI_RELEASE_CANDIDATE_NOT_SHIPPED",
        "bounded_claim": ALLOWED_CLAIM,
        "execution_axes": list(AXES),
        "claims_not_observed": list(CLAIMS_NOT_OBSERVED),
    }
    for field, expected in invariant_values.items():
        if receipt[field] != expected:
            raise WorkflowError(f"receipt invariant mismatch for {field}")
    checks = {
        "source-manifest.json": receipt["source_manifest_sha256"],
        "TRIAD_REPORT.md": receipt["report_sha256"],
    }
    for name, expected in checks.items():
        path = run_dir / name
        if not path.is_file():
            raise WorkflowError(f"run artifact is missing: {name}")
        actual = sha256_bytes(path.read_bytes())
        if actual != expected:
            raise WorkflowError(f"run artifact hash mismatch for {name}: expected {expected}, observed {actual}")


def replay_packet(packet: dict[str, Any], base_dir: pathlib.Path, run_dir: pathlib.Path) -> None:
    expected = build_artifacts(packet, base_dir)
    for name, content in expected.items():
        path = run_dir / name
        if not path.is_file() or path.read_bytes() != content:
            raise WorkflowError(f"replay differs for {name}")
