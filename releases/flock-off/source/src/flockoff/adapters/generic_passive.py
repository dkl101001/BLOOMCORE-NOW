"""Capability-gated normalizer for a future broad passive receiver.

This is an input boundary, not a capture driver. It prevents the target-filtered
Flock-You stream from being mislabeled as general unknown-emitter discovery.
    """

from __future__ import annotations

from typing import Any

from ..canonical import keyed_digest, rotating_identifier
from ..hardware import require_capability
from .common import finalize_observation, raw_digest

ADAPTER_VERSION = "0.1.0"


def normalize_feature_record(
    payload: dict[str, Any], *, observed_at_utc: str, ingested_at_utc: str,
    receiver_id: str, hardware_profile: dict[str, Any], rotation_epoch: str,
    rotation_secret: bytes, pose_ref: str | None = None,
    trusted_hardware_profile: bool = False,
) -> dict[str, Any]:
    if trusted_hardware_profile is not True:
        raise RuntimeError("generic passive adapter requires a trusted local hardware profile")
    if payload.get("capture_mode") != "PASSIVE_RECEIVE_ONLY":
        raise ValueError("generic adapter requires an explicit receive-only capture mode")
    protocol = payload.get("protocol")
    if protocol not in {"WIFI_80211", "BLUETOOTH_LE", "SPECTRUM"}:
        raise ValueError("unsupported generic passive protocol")
    band = payload.get("band")
    capability = require_capability(hardware_profile, protocol, band)
    allowed_kinds = {
        "WIFI_80211": {"WIFI_DETECTION", "SPECTRUM_FEATURE"},
        "BLUETOOTH_LE": {"SPECTRUM_FEATURE"},
        "SPECTRUM": {"SPECTRUM_FEATURE"},
    }
    measurement_kind = payload.get("measurement_kind", "SPECTRUM_FEATURE")
    if measurement_kind not in allowed_kinds[protocol]:
        raise ValueError("measurement kind exceeds the verified generic passive boundary")
    asserted_values = payload.get("capabilities", [])
    if not isinstance(asserted_values, list) or any(not isinstance(item, str) for item in asserted_values):
        raise ValueError("event capabilities must be a string array")
    asserted_capabilities = set(asserted_values)
    verified_measurements = set(capability["measurement_types"])
    if asserted_capabilities - verified_measurements:
        raise ValueError("event asserts capabilities absent from the verified hardware profile")
    if measurement_kind not in verified_measurements:
        raise ValueError("measurement kind is absent from the verified hardware profile")
    raw_identifier = payload.get("identifier")
    ephemeral = None
    if raw_identifier:
        ephemeral = rotating_identifier(rotation_secret, rotation_epoch, str(raw_identifier))
    operational_digest = raw_digest(
        payload, secret=rotation_secret, rotation_epoch=rotation_epoch
    )
    raw_features = payload.get("feature_hashes", [])
    if not isinstance(raw_features, list) or any(not isinstance(item, str) for item in raw_features):
        raise ValueError("feature hashes must be a string array")
    feature_hashes = sorted({
        keyed_digest(rotation_secret, f"generic-feature:{rotation_epoch}", item)
        for item in raw_features
    })
    observation = {
        "schema_version": "1.0.0",
        "observed_at_utc": observed_at_utc,
        "clock_uncertainty_ms": float(payload.get("clock_uncertainty_ms", 1000.0)),
        "timing": {
            "host_received_at_utc": ingested_at_utc,
            "host_monotonic_ns": payload.get("host_monotonic_ns"),
            "sensor_boot_id": payload.get("sensor_boot_id"),
            "source_sequence": payload.get("source_sequence"),
            "source_time_state": payload.get("source_time_state", "HOST_RECEIPT_ONLY"),
            "clock_epoch_id": payload.get("clock_epoch_id", "host-clock-epoch-0"),
        },
        "measurement_lineage_id": f"receiver:{receiver_id}:generic:{rotation_epoch}",
        "receiver": {"receiver_id": receiver_id, "pose_ref": pose_ref, "calibration_profile_id": payload.get("calibration_profile_id")},
        "sensor": {
            "adapter_id": "generic_passive_feature_record",
            "adapter_version": ADAPTER_VERSION,
            "hardware_profile_id": hardware_profile["hardware_profile_id"],
            "protocol": protocol,
            "band": band,
            "channel": payload.get("channel"),
            "center_frequency_hz": payload.get("center_frequency_hz"),
            "bandwidth_hz": payload.get("bandwidth_hz"),
            "capabilities": sorted(verified_measurements),
        },
        "emitter": {
            "ephemeral_emitter_key": ephemeral,
            "target_identifier": None,
            "identifier_type": payload.get("identifier_type"),
            "identifier_retention": "ROTATING_HASH" if ephemeral else "NONE",
            "address_randomization_state": payload.get("address_randomization_state", "UNKNOWN"),
        },
        "measurement": {
            "kind": measurement_kind,
            "rssi_dbm": payload.get("rssi_dbm"),
            "snr_db": payload.get("snr_db"),
            "frame_type": payload.get("frame_type"),
            "detection_method": "generic_passive_feature_record",
            "upstream_tier": None,
            "feature_hashes": feature_hashes,
            "payload_digest": operational_digest,
            "bearing_deg": None,
            "bearing_uncertainty_deg": None,
            "tdoa_seconds": None,
            "tdoa_uncertainty_seconds": None,
            "remote_id": None,
            "extensions": {},
        },
        "privacy": {
            "class": "OPERATIONAL_MINIMIZED",
            "raw_retained": False,
            "public_export_allowed": False,
            "rotation_epoch": rotation_epoch,
        },
        "provenance": {
            "adapter_source_ref": "flockoff:generic-passive-interface",
            "adapter_commit_or_version": ADAPTER_VERSION,
            "raw_input_digest": operational_digest,
            "normalizer_version": ADAPTER_VERSION,
            "ingested_at_utc": ingested_at_utc,
            "raw_capture_ref": None,
        },
    }
    return finalize_observation(observation)
