"""Fail-closed, approval-bound projection for route-safe local draft exports."""

from __future__ import annotations

import datetime as dt
import math
import re
from copy import deepcopy
from typing import Any

from .canonical import content_id, sha256_uri, without_keys

POLICY_VERSION = "public-export-1.0.0"
REVIEW_STATE = "LOCAL_DRAFT"
APPROVAL_SCOPE = "LOCAL_DRAFT_ONLY"

_ELIGIBLE_PUBLICATION_STATES = {
    "READY_FOR_REVIEW", "PUBLIC_CANDIDATE", "PUBLIC_VERIFIED", "SHARED_REDACTED",
}
_COUNT_KEYS = {
    "WIFI_80211", "BLUETOOTH_LE", "REMOTE_ID", "BEARING", "TDOA",
    "SPECTRUM", "PUBLIC_RECORD",
}
_REDACTIONS = [
    "observer route and exact observation times",
    "raw and pseudonymous emitter identifiers",
    "Remote ID operator/control/takeoff positions",
    "raw capture references and local storage paths",
]
_ACKNOWLEDGEMENTS = {
    "route_data_excluded": True,
    "raw_identifiers_excluded": True,
    "remote_id_operator_positions_excluded": True,
    "contradictions_preserved": True,
    "no_automatic_publication": True,
}
_APPROVAL_KEYS = {
    "schema_version", "approval_id", "approval_type", "scope", "policy_version",
    "request_digest", "approved_at_utc", "acknowledgements",
}
_BUNDLE_KEYS = {
    "schema_version", "export_id", "policy_version", "review_state",
    "publication_approval", "generated_from_receipts", "nodes", "public_evidence",
    "aggregate_observation_counts", "redactions", "route_data_included",
}
_NODE_KEYS = {
    "node_id", "revision", "motion_state", "asset_kind_hypotheses", "claim_level",
    "classification", "location", "public_evidence_refs", "contradiction_refs", "receipt_id",
}
_EVIDENCE_KEYS = {
    "evidence_id", "source_id", "source_lineage_id", "parent_source_ids", "source_type",
    "authority_role", "independence_class", "retrieved_at_utc", "claim",
    "license_or_terms", "source_locator", "content_hash",
}
_CLAIM_KEYS = {
    "claim_type", "claim_text", "node_type", "vendor", "model", "geometry",
    "coordinate_uncertainty_m", "bearing_deg", "status",
}
_RECEIPT_RE = re.compile(r"^receipt_[a-f0-9]{32,64}$")
_DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_URL_RE = re.compile(r"^https?://")

PROHIBITED_KEYS = {
    "receiver", "receiver_id", "pose_ref", "pose_id", "observed_at_utc",
    "host_received_at_utc", "host_monotonic_ns", "timing", "trajectory",
    "mac_address", "target_identifier", "ephemeral_emitter_key", "rotation_epoch",
    "uas_id", "operator_or_takeoff_position", "raw_capture_ref", "raw_input_digest",
    "payload_digest", "local_path", "evidence_refs",
}


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing or unknown:
        raise ValueError(f"{label} key mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}")
    return value


def _utc_timestamp(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a UTC timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} is not an ISO date-time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        raise ValueError(f"{label} must include a UTC offset")
    return value


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def _position(value: Any, label: str) -> list[int | float]:
    if not isinstance(value, list) or len(value) not in {2, 3}:
        raise ValueError(f"{label} must be a two- or three-number coordinate")
    for index, coordinate in enumerate(value):
        _finite_number(coordinate, f"{label}[{index}]")
    if not -180 <= value[0] <= 180 or not -90 <= value[1] <= 90:
        raise ValueError(f"{label} is outside geographic bounds")
    return deepcopy(value)


def _ring(value: Any, label: str) -> list[list[int | float]]:
    if not isinstance(value, list) or len(value) < 4:
        raise ValueError(f"{label} must contain at least four positions")
    ring = [_position(point, f"{label}[{index}]") for index, point in enumerate(value)]
    if ring[0][:2] != ring[-1][:2]:
        raise ValueError(f"{label} must be closed")
    return ring


def _geometry(value: Any, *, allow_point: bool, label: str) -> dict[str, Any]:
    _exact_keys(value, {"type", "coordinates"}, label)
    geometry_type = value["type"]
    coordinates = value["coordinates"]
    if geometry_type == "Point" and allow_point:
        projected = _position(coordinates, f"{label}.coordinates")
    elif geometry_type == "Polygon":
        if not isinstance(coordinates, list) or not coordinates:
            raise ValueError(f"{label}.coordinates must contain a ring")
        projected = [_ring(ring, f"{label}.coordinates[{index}]") for index, ring in enumerate(coordinates)]
    elif geometry_type == "MultiPolygon":
        if not isinstance(coordinates, list) or not coordinates:
            raise ValueError(f"{label}.coordinates must contain a polygon")
        projected = []
        for polygon_index, polygon in enumerate(coordinates):
            if not isinstance(polygon, list) or not polygon:
                raise ValueError(f"{label}.coordinates[{polygon_index}] must contain a ring")
            projected.append([
                _ring(ring, f"{label}.coordinates[{polygon_index}][{ring_index}]")
                for ring_index, ring in enumerate(polygon)
            ])
    else:
        allowed = "Point, Polygon or MultiPolygon" if allow_point else "Polygon or MultiPolygon"
        raise ValueError(f"{label}.type must be {allowed}")
    return {"type": geometry_type, "coordinates": projected}


def _classification(value: Any) -> dict[str, Any]:
    expected = {"ranked_labels", "probabilities", "calibration_state", "confidence_label"}
    _exact_keys(value, expected, "classification")
    labels = value["ranked_labels"]
    if not isinstance(labels, list) or not labels or any(not isinstance(item, str) or not item for item in labels):
        raise ValueError("classification.ranked_labels must be non-empty strings")
    if len(labels) != len(set(labels)):
        raise ValueError("classification.ranked_labels must be unique")
    calibration = value["calibration_state"]
    if calibration not in {"UNCALIBRATED", "INTERNALLY_CALIBRATED", "EXTERNALLY_VALIDATED"}:
        raise ValueError("invalid classification calibration state")
    probabilities = value["probabilities"]
    if calibration == "UNCALIBRATED" and probabilities is not None:
        raise ValueError("uncalibrated classification cannot publish probabilities")
    if probabilities is not None:
        if not isinstance(probabilities, dict):
            raise ValueError("classification.probabilities must be an object or null")
        for key, probability in probabilities.items():
            if not isinstance(key, str) or not key:
                raise ValueError("classification probability labels must be non-empty")
            number = _finite_number(probability, f"classification.probabilities.{key}")
            if not 0 <= number <= 1:
                raise ValueError("classification probability must be between zero and one")
    if value["confidence_label"] not in {"LOW", "MODERATE", "HIGH", "UNKNOWN"}:
        raise ValueError("invalid classification confidence label")
    return deepcopy(value)


def _node_location(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    expected = {"geometry_type", "geojson", "calibration_state", "confidence_level", "area_m2", "method"}
    _exact_keys(value, expected, "node.location")
    calibration = value["calibration_state"]
    if calibration not in {"UNCALIBRATED", "INTERNALLY_CALIBRATED", "EXTERNALLY_VALIDATED"}:
        raise ValueError("invalid location calibration state")
    confidence = value["confidence_level"]
    if calibration == "UNCALIBRATED" and confidence is not None:
        raise ValueError("uncalibrated location cannot publish confidence")
    if confidence is not None and not 0 <= _finite_number(confidence, "location.confidence_level") <= 1:
        raise ValueError("location confidence must be between zero and one")
    if _finite_number(value["area_m2"], "location.area_m2") <= 0:
        raise ValueError("location area must be positive")
    projected = deepcopy(value)
    projected["geojson"] = _geometry(value["geojson"], allow_point=False, label="node.location.geojson")
    return projected


def _project_node(node: Any, *, public_evidence_ids: set[str]) -> dict[str, Any] | None:
    if not isinstance(node, dict):
        raise ValueError("node revision must be an object")
    if node.get("publication_state") not in _ELIGIBLE_PUBLICATION_STATES:
        return None
    source_required = (_NODE_KEYS - {"public_evidence_refs"}) | {"evidence_refs"}
    missing = source_required - set(node)
    if missing:
        raise ValueError(f"node revision lacks public projection fields: {sorted(missing)}")
    if not isinstance(node["evidence_refs"], list):
        raise ValueError("node revision evidence_refs must be a list")
    unknown_public_refs = sorted(
        ref for ref in node["evidence_refs"]
        if isinstance(ref, str) and ref.startswith("pub_") and ref not in public_evidence_ids
    )
    if unknown_public_refs:
        raise ValueError(f"node references public evidence not supplied to the export: {unknown_public_refs}")
    projected = {
        key: deepcopy(node[key])
        for key in _NODE_KEYS - {"public_evidence_refs"}
    }
    projected["public_evidence_refs"] = sorted(
        ref for ref in node["evidence_refs"] if ref in public_evidence_ids
    )
    projected["classification"] = _classification(node["classification"])
    projected["location"] = _node_location(node["location"])
    _validate_projected_node(projected, public_evidence_ids=public_evidence_ids)
    return projected


def _validate_projected_node(node: Any, *, public_evidence_ids: set[str] | None = None) -> None:
    _exact_keys(node, _NODE_KEYS, "public node")
    if not isinstance(node["node_id"], str) or not re.fullmatch(r"node_[a-f0-9]{16,64}", node["node_id"]):
        raise ValueError("invalid public node ID")
    if isinstance(node["revision"], bool) or not isinstance(node["revision"], int) or node["revision"] < 1:
        raise ValueError("invalid public node revision")
    if not _RECEIPT_RE.fullmatch(str(node["receipt_id"])):
        raise ValueError("invalid public node receipt ID")
    _classification(node["classification"])
    _node_location(node["location"])
    for key in ("public_evidence_refs", "contradiction_refs"):
        refs = node[key]
        if not isinstance(refs, list):
            raise ValueError(f"public node {key} must be a list")
        if any(not isinstance(ref, str) or not ref for ref in refs) or len(refs) != len(set(refs)):
            raise ValueError(f"public node {key} must contain unique non-empty references")
    if any(not re.fullmatch(r"pub_[a-f0-9]{32,64}", ref) for ref in node["public_evidence_refs"]):
        raise ValueError("public node contains a non-public evidence reference")
    if public_evidence_ids is not None:
        unknown = sorted(set(node["public_evidence_refs"]) - public_evidence_ids)
        if unknown:
            raise ValueError(f"public node references evidence absent from the bundle: {unknown}")


def _claim(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("public evidence claim must be an object")
    unknown = set(value) - _CLAIM_KEYS
    if unknown:
        raise ValueError(f"public evidence claim has non-allowlisted keys: {sorted(unknown)}")
    if not {"claim_type", "claim_text"} <= set(value):
        raise ValueError("public evidence claim lacks claim_type or claim_text")
    projected = {key: deepcopy(value[key]) for key in _CLAIM_KEYS if key in value}
    if "geometry" in projected and projected["geometry"] is not None:
        projected["geometry"] = _geometry(projected["geometry"], allow_point=True, label="public evidence geometry")
    return projected


def _project_evidence(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("public evidence must be an object")
    required = {
        "evidence_id", "source_id", "source_lineage_id", "parent_source_ids", "source_type",
        "authority_role", "independence_class", "retrieved_at_utc", "claim", "provenance",
    }
    missing = required - set(item)
    if missing:
        raise ValueError(f"public evidence lacks fields: {sorted(missing)}")
    provenance = item["provenance"]
    if not isinstance(provenance, dict) or not {"source_locator", "content_hash"} <= set(provenance):
        raise ValueError("public evidence provenance lacks source locator or content hash")
    projected = {
        "evidence_id": item["evidence_id"],
        "source_id": item["source_id"],
        "source_lineage_id": item["source_lineage_id"],
        "parent_source_ids": deepcopy(item["parent_source_ids"]),
        "source_type": item["source_type"],
        "authority_role": item["authority_role"],
        "independence_class": item["independence_class"],
        "retrieved_at_utc": item["retrieved_at_utc"],
        "claim": _claim(item["claim"]),
        "license_or_terms": item.get("license_or_terms"),
        "source_locator": provenance["source_locator"],
        "content_hash": provenance["content_hash"],
    }
    _validate_projected_evidence(projected)
    return projected


def _validate_projected_evidence(item: Any) -> None:
    _exact_keys(item, _EVIDENCE_KEYS, "projected public evidence")
    if not isinstance(item["license_or_terms"], str) or not item["license_or_terms"].strip():
        raise ValueError("public evidence requires a non-empty license or terms statement")
    if not isinstance(item["source_locator"], str) or not _URL_RE.match(item["source_locator"]):
        raise ValueError("public source locator must be an HTTP(S) URL")
    if not isinstance(item["content_hash"], str) or not _DIGEST_RE.fullmatch(item["content_hash"]):
        raise ValueError("public evidence content hash is invalid")
    _utc_timestamp(item["retrieved_at_utc"], "public evidence retrieved_at_utc")
    _claim(item["claim"])


def _receipt_ids(values: Any) -> list[str]:
    if not isinstance(values, list) or not values:
        raise ValueError("at least one evidence receipt is required")
    if any(not isinstance(value, str) or not _RECEIPT_RE.fullmatch(value) for value in values):
        raise ValueError("invalid evidence receipt ID")
    return sorted(set(values))


def _counts(values: Any) -> dict[str, int]:
    if not isinstance(values, dict):
        raise ValueError("aggregate counts must be an object")
    unknown = set(values) - _COUNT_KEYS
    if unknown:
        raise ValueError(f"aggregate count has non-allowlisted keys: {sorted(unknown)}")
    for key, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"aggregate count {key} must be a non-negative integer")
    return {key: values[key] for key in sorted(values)}


def _projection(
    *, node_revisions: list[dict[str, Any]], public_evidence: list[dict[str, Any]],
    receipt_ids: list[str], aggregate_counts: dict[str, int],
) -> dict[str, Any]:
    receipts = _receipt_ids(receipt_ids)
    projected_evidence = sorted((_project_evidence(item) for item in public_evidence), key=lambda item: item["evidence_id"])
    evidence_ids = [item["evidence_id"] for item in projected_evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("duplicate public evidence IDs")
    evidence_id_set = set(evidence_ids)
    projected_nodes = [
        projected for node in node_revisions
        if (projected := _project_node(node, public_evidence_ids=evidence_id_set)) is not None
    ]
    projected_nodes.sort(key=lambda node: (node["node_id"], node["revision"]))
    node_keys = [(node["node_id"], node["revision"]) for node in projected_nodes]
    if len(node_keys) != len(set(node_keys)):
        raise ValueError("duplicate public node revisions")
    receipt_set = set(receipts)
    missing_receipts = sorted({node["receipt_id"] for node in projected_nodes} - receipt_set)
    if missing_receipts:
        raise ValueError(f"public nodes are missing receipt closure: {missing_receipts}")
    return {
        "policy_version": POLICY_VERSION,
        "review_state": REVIEW_STATE,
        "generated_from_receipts": receipts,
        "nodes": projected_nodes,
        "public_evidence": projected_evidence,
        "aggregate_observation_counts": _counts(aggregate_counts),
        "redactions": list(_REDACTIONS),
        "route_data_included": False,
    }


def _projection_digest(projection: dict[str, Any]) -> str:
    return sha256_uri(projection)


def publication_request_digest(
    *, node_revisions: list[dict[str, Any]], public_evidence: list[dict[str, Any]],
    receipt_ids: list[str], aggregate_counts: dict[str, int],
) -> str:
    """Hash the exact allowlisted projection that a local operator must approve."""

    return _projection_digest(_projection(
        node_revisions=node_revisions,
        public_evidence=public_evidence,
        receipt_ids=receipt_ids,
        aggregate_counts=aggregate_counts,
    ))


def make_local_draft_approval(
    *, request_digest: str, approved_at_utc: str, operator_confirmation: bool,
) -> dict[str, Any]:
    """Create a content-addressed opt-in artifact after an explicit local confirmation."""

    if operator_confirmation is not True:
        raise ValueError("local operator confirmation is required")
    if not isinstance(request_digest, str) or not _DIGEST_RE.fullmatch(request_digest):
        raise ValueError("invalid publication request digest")
    _utc_timestamp(approved_at_utc, "approved_at_utc")
    body = {
        "schema_version": "1.0.0",
        "approval_type": "LOCAL_OPERATOR_OPT_IN",
        "scope": APPROVAL_SCOPE,
        "policy_version": POLICY_VERSION,
        "request_digest": request_digest,
        "approved_at_utc": approved_at_utc,
        "acknowledgements": dict(_ACKNOWLEDGEMENTS),
    }
    return {**body, "approval_id": content_id("approval", body, 40)}


def verify_local_draft_approval(approval: Any, *, expected_request_digest: str) -> None:
    """Reject stale, broadened, malformed or content-tampered approval artifacts."""

    _exact_keys(approval, _APPROVAL_KEYS, "publication approval")
    if approval["schema_version"] != "1.0.0":
        raise ValueError("unsupported publication approval schema")
    if approval["approval_type"] != "LOCAL_OPERATOR_OPT_IN":
        raise ValueError("publication approval is not an explicit local opt-in")
    if approval["scope"] != APPROVAL_SCOPE or approval["policy_version"] != POLICY_VERSION:
        raise ValueError("publication approval scope or policy does not match")
    if approval["request_digest"] != expected_request_digest:
        raise ValueError("publication approval does not bind this exact projection")
    _utc_timestamp(approval["approved_at_utc"], "publication approval approved_at_utc")
    if approval["acknowledgements"] != _ACKNOWLEDGEMENTS:
        raise ValueError("publication approval acknowledgements are incomplete")
    expected_id = content_id("approval", without_keys(approval, "approval_id"), 40)
    if approval["approval_id"] != expected_id:
        raise ValueError("publication approval content ID mismatch")


def build_public_bundle(
    *, node_revisions: list[dict[str, Any]], public_evidence: list[dict[str, Any]],
    receipt_ids: list[str], aggregate_counts: dict[str, int],
    approval: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a route-safe LOCAL_DRAFT; this function cannot produce a published artifact."""

    projection = _projection(
        node_revisions=node_revisions,
        public_evidence=public_evidence,
        receipt_ids=receipt_ids,
        aggregate_counts=aggregate_counts,
    )
    request_digest = _projection_digest(projection)
    if approval is None:
        raise ValueError("an explicit local-draft publication approval artifact is required")
    verify_local_draft_approval(approval, expected_request_digest=request_digest)
    base = {
        "schema_version": "1.0.0",
        **projection,
        "publication_approval": deepcopy(approval),
    }
    bundle = {**base, "export_id": content_id("export", base, 40)}
    assert_route_safe(bundle)
    return bundle


def _find_prohibited(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in PROHIBITED_KEYS:
                findings.append(child_path)
            findings.extend(_find_prohibited(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_find_prohibited(child, f"{path}[{index}]"))
    return findings


def assert_route_safe(bundle: dict[str, Any]) -> None:
    """Validate the closed public projection and its approval/content bindings."""

    _exact_keys(bundle, _BUNDLE_KEYS, "public export bundle")
    if bundle["schema_version"] != "1.0.0" or bundle["policy_version"] != POLICY_VERSION:
        raise ValueError("unsupported public export schema or policy")
    if bundle["review_state"] != REVIEW_STATE or bundle["route_data_included"] is not False:
        raise ValueError("only route-free LOCAL_DRAFT exports are supported")
    if bundle["redactions"] != _REDACTIONS:
        raise ValueError("required public export redactions are missing")
    receipts = _receipt_ids(bundle["generated_from_receipts"])
    if receipts != bundle["generated_from_receipts"]:
        raise ValueError("public export receipt IDs must be sorted and unique")
    for item in bundle["public_evidence"]:
        _validate_projected_evidence(item)
    evidence_ids = {item["evidence_id"] for item in bundle["public_evidence"]}
    for node in bundle["nodes"]:
        _validate_projected_node(node, public_evidence_ids=evidence_ids)
        if node["receipt_id"] not in receipts:
            raise ValueError("public node lacks receipt closure")
    _counts(bundle["aggregate_observation_counts"])
    projection = {
        "policy_version": bundle["policy_version"],
        "review_state": bundle["review_state"],
        "generated_from_receipts": bundle["generated_from_receipts"],
        "nodes": bundle["nodes"],
        "public_evidence": bundle["public_evidence"],
        "aggregate_observation_counts": bundle["aggregate_observation_counts"],
        "redactions": bundle["redactions"],
        "route_data_included": bundle["route_data_included"],
    }
    verify_local_draft_approval(
        bundle["publication_approval"],
        expected_request_digest=_projection_digest(projection),
    )
    expected_export_id = content_id("export", without_keys(bundle, "export_id"), 40)
    if bundle["export_id"] != expected_export_id:
        raise ValueError("public export content ID mismatch")
    findings = _find_prohibited(bundle)
    if findings:
        raise ValueError(f"public export leak guard rejected: {findings}")
