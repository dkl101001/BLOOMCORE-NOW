"""Explainable, claim-ceiling signature evaluation."""

from __future__ import annotations

from typing import Any

from . import CODE_REVISION, runtime_source_digest
from .canonical import content_id, sha256_uri


def _feature(observation: dict[str, Any], feature_id: str) -> Any:
    sensor = observation["sensor"]
    measurement = observation["measurement"]
    upstream = measurement.get("extensions", {}).get("upstream_assertion", {})
    mapping = {
        "sensor.protocol": sensor.get("protocol"),
        "sensor.band": sensor.get("band"),
        "upstream.method": upstream.get("method"),
        "upstream.tier": upstream.get("tier"),
        "upstream.observed_prefix": upstream.get("observed_prefix"),
    }
    return mapping.get(feature_id)


def _gate_result(actual: Any, gate: dict[str, Any]) -> tuple[str, str]:
    operator, expected = gate["operator"], gate.get("expected")
    if actual is None:
        return "NOT_OBSERVED", "feature was not carried by the normalized observation"
    passed = False
    if operator == "EQUALS":
        passed = actual == expected
    elif operator == "IN":
        passed = actual in expected
    elif operator == "PREFIX_IN":
        passed = str(actual).lower() in {str(x).lower() for x in expected}
    elif operator == "PRESENT":
        passed = actual is not None
    elif operator == "ABSENT":
        passed = actual is None
    elif operator == "RANGE":
        passed = expected[0] <= actual <= expected[1]
    elif operator == "HASH_EQUALS":
        passed = actual == expected
    else:
        return "NOT_OBSERVED", f"unsupported operator {operator}"
    return ("PASSED", f"observed value satisfies {operator}") if passed else (
        "FAILED", f"observed value does not satisfy {operator}"
    )


def evaluate(
    observation: dict[str, Any], signature: dict[str, Any], *, trusted_registry: bool = False
) -> dict[str, Any]:
    results = []
    required_failed = False
    required_unknown = False
    for gate in signature["feature_gates"]:
        state, explanation = _gate_result(_feature(observation, gate["feature_id"]), gate)
        results.append({"feature_id": gate["feature_id"], "state": state, "explanation": explanation})
        if gate["required"] and state == "FAILED":
            required_failed = True
        if gate["required"] and state == "NOT_OBSERVED":
            required_unknown = True
    if signature["status"] == "RETIRED":
        match_state = "NOT_EVALUABLE"
        results.append({
            "feature_id": "signature.lifecycle",
            "state": "CONTRADICTORY",
            "explanation": "retired signatures cannot create current matches",
        })
    elif required_failed:
        match_state = "NO_MATCH"
    elif required_unknown:
        match_state = "NOT_EVALUABLE"
    else:
        match_state = "MATCH"
    validation = signature["validation"]
    activation_valid = (
        signature["status"] == "ACTIVE"
        and validation["calibration_state"] in {"INTERNALLY_CALIBRATED", "EXTERNALLY_VALIDATED"}
        and validation["leave_one_device_out"] is True
        and validation["validation_receipt_ref"] is not None
        and validation["false_positive_upper_95"] is not None
        and validation["false_positive_upper_95"] <= 0.01
    )
    if match_state != "MATCH":
        claim_ceiling = "RF_ACTIVITY_PRESENT"
    elif trusted_registry and activation_valid:
        claim_ceiling = signature["claim_ceiling"]
    else:
        claim_ceiling = "RF_PATTERN"
    base = {
        "schema_version": "1.0.0",
        "observation_refs": [observation["observation_id"]],
        "signature_ref": {
            "signature_id": signature["signature_id"],
            "version": signature["version"],
            "content_hash": signature["provenance"]["content_hash"],
        },
        "match_state": match_state,
        "feature_results": results,
        "claim_ceiling": claim_ceiling,
        "calibration_state": validation["calibration_state"],
        "probability": None,
        "algorithm": {
            "name": "declarative_feature_gate",
            "version": "1.0.0",
            "code_revision": CODE_REVISION,
            "code_digest": runtime_source_digest(),
        },
    }
    base["match_id"] = content_id("match", base, 40)
    return base


def signature_content_hash(signature: dict[str, Any]) -> str:
    clone = {**signature, "provenance": {**signature["provenance"], "content_hash": ""}}
    return sha256_uri(clone)
