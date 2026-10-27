"""Normalize already-decoded ASTM/FAA Broadcast Remote ID messages.

Live radio decoding is deliberately delegated to a pinned OpenDroneID adapter.
This code neither transmits nor connects to the observed aircraft.
"""

from __future__ import annotations

import math
from typing import Any

from ..canonical import rotating_identifier
from .common import finalize_observation, raw_digest

RECEIVER_URL = "https://github.com/opendroneid/receiver-android"
RECEIVER_RELEASE = "v3.7.0"
RECEIVER_REVISION = "v3.7.0@60b4320"
CORE_URL = "https://github.com/opendroneid/opendroneid-core-c"
CORE_REVISION = "master@ec44332"
STANDARD_PROFILE_REF = "ASTM-F3411-22a+14-CFR-Part-89-as-of-2026-08-23"
ADAPTER_VERSION = "0.3.0"
TRANSPORTS = {
    "bluetooth_legacy": "BLUETOOTH_LEGACY",
    "bluetooth_5_long_range": "BLUETOOTH_5_LONG_RANGE",
    "wifi_nan": "WIFI_NAN",
    "wifi_beacon": "WIFI_BEACON",
}


def _position(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Remote ID position must be an object")
    lat, lon = value.get("latitude"), value.get("longitude")
    if isinstance(lat, bool) or not isinstance(lat, (int, float)) or not math.isfinite(lat) or not -90 <= lat <= 90:
        raise ValueError("invalid Remote ID latitude")
    if isinstance(lon, bool) or not isinstance(lon, (int, float)) or not math.isfinite(lon) or not -180 <= lon <= 180:
        raise ValueError("invalid Remote ID longitude")
    altitude = value.get("altitude_m")
    accuracy = value.get("horizontal_accuracy_m")
    if altitude is not None and (
        isinstance(altitude, bool) or not isinstance(altitude, (int, float))
        or not math.isfinite(altitude)
    ):
        raise ValueError("invalid Remote ID altitude")
    if accuracy is not None and (
        isinstance(accuracy, bool) or not isinstance(accuracy, (int, float))
        or not math.isfinite(accuracy) or accuracy < 0
    ):
        raise ValueError("invalid Remote ID horizontal accuracy")
    return {
        "latitude": float(lat),
        "longitude": float(lon),
        "altitude_m": altitude,
        "horizontal_accuracy_m": accuracy,
    }


def _finite_optional(value: Any, name: str, *, minimum: float | None = None,
                     maximum_exclusive: float | None = None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"invalid Remote ID {name}")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"invalid Remote ID {name}")
    if maximum_exclusive is not None and result >= maximum_exclusive:
        raise ValueError(f"invalid Remote ID {name}")
    return result


def normalize(
    payload: dict[str, Any],
    *,
    observed_at_utc: str,
    ingested_at_utc: str,
    receiver_id: str,
    hardware_profile_id: str,
    rotation_epoch: str,
    rotation_secret: bytes,
    pose_ref: str | None = None,
    clock_uncertainty_ms: float = 1000.0,
    host_monotonic_ns: int | None = None,
    sensor_boot_id: str | None = None,
    source_sequence: int | None = None,
    clock_epoch_id: str = "host-clock-epoch-0",
    source_time_state: str = "HOST_RECEIPT_ONLY",
    measurement_lineage_id: str | None = None,
    upstream_receiver_revision: str = RECEIVER_REVISION,
) -> dict[str, Any]:
    transport = TRANSPORTS.get(str(payload.get("transport", "")).lower())
    if transport is None:
        raise ValueError("unsupported or missing Remote ID transport")
    validity = str(payload.get("validity", "UNVERIFIED")).upper()
    if validity not in {"VALID", "UNVERIFIED", "INCOMPLETE", "MALFORMED", "CONTRADICTED"}:
        raise ValueError("invalid Remote ID validity")
    uas_id = payload.get("uas_id")
    operational_digest = raw_digest(payload, secret=rotation_secret, rotation_epoch=rotation_epoch)
    identifier_seed = str(uas_id) if uas_id else str(payload.get("session_key") or operational_digest)
    emitter_key = rotating_identifier(rotation_secret, rotation_epoch, identifier_seed)
    aircraft_position = None if validity == "MALFORMED" else _position(payload.get("aircraft_position"))
    # Validate a supplied restricted position, then discard it at the privacy
    # firewall. The MVP has no separately encrypted RID-operator vault, so it
    # must not enter the ordinary observation or SQLite event table.
    if validity != "MALFORMED" and payload.get("operator_or_takeoff_position") is not None:
        _position(payload.get("operator_or_takeoff_position"))
    claimed_authentication = str(payload.get("authentication_state", "NOT_CHECKED")).upper()
    if claimed_authentication not in {"NOT_PRESENT", "NOT_CHECKED", "VALID", "INVALID", "UNKNOWN"}:
        raise ValueError("invalid Remote ID authentication state")
    authentication_state = (
        "NOT_PRESENT" if claimed_authentication == "NOT_PRESENT" else "NOT_CHECKED"
    )
    if source_time_state not in {"SOURCE_TIMESTAMPED", "HOST_RECEIPT_ONLY", "CLOCK_CONTRADICTED"}:
        raise ValueError("invalid Remote ID source time state")
    speed_mps = _finite_optional(payload.get("speed_mps"), "speed", minimum=0)
    heading_deg = _finite_optional(
        payload.get("heading_deg"), "heading", minimum=0, maximum_exclusive=360
    )
    height_m = _finite_optional(payload.get("height_m"), "height")
    rssi_dbm = _finite_optional(payload.get("rssi_dbm"), "RSSI")
    snr_db = _finite_optional(payload.get("snr_db"), "SNR")
    observation = {
        "schema_version": "1.0.0",
        "observed_at_utc": observed_at_utc,
        "clock_uncertainty_ms": clock_uncertainty_ms,
        "timing": {
            "host_received_at_utc": ingested_at_utc,
            "host_monotonic_ns": host_monotonic_ns,
            "sensor_boot_id": sensor_boot_id,
            "source_sequence": source_sequence,
            "source_time_state": source_time_state,
            "clock_epoch_id": clock_epoch_id,
        },
        "measurement_lineage_id": measurement_lineage_id
            or f"receiver:{receiver_id}:remote-id:{rotation_epoch}",
        "receiver": {"receiver_id": receiver_id, "pose_ref": pose_ref, "calibration_profile_id": None},
        "sensor": {
            "adapter_id": "opendroneid_decoded_json",
            "adapter_version": ADAPTER_VERSION,
            "hardware_profile_id": hardware_profile_id,
            "protocol": "REMOTE_ID",
            "band": payload.get("band"),
            "channel": payload.get("channel"),
            "center_frequency_hz": payload.get("center_frequency_hz"),
            "bandwidth_hz": None,
            "capabilities": ["PASSIVE_REMOTE_ID_RECEPTION", transport],
        },
        "emitter": {
            "ephemeral_emitter_key": emitter_key,
            "target_identifier": None,
            "identifier_type": payload.get("uas_id_type"),
            "identifier_retention": "ROTATING_HASH",
            "address_randomization_state": "NOT_APPLICABLE",
        },
        "measurement": {
            "kind": "REMOTE_ID_BROADCAST",
            "rssi_dbm": rssi_dbm,
            "snr_db": snr_db,
            "frame_type": None,
            "detection_method": "decoded_broadcast_remote_id",
            "upstream_tier": None,
            "feature_hashes": [],
            "payload_digest": operational_digest,
            "bearing_deg": None,
            "bearing_uncertainty_deg": None,
            "tdoa_seconds": None,
            "tdoa_uncertainty_seconds": None,
            "remote_id": {
                "transport": transport,
                "validity": validity,
                "uas_id_type": payload.get("uas_id_type"),
                "uas_id": None,
                "aircraft_position_source": "BROADCAST_REMOTE_ID",
                "aircraft_position": aircraft_position,
                "operator_or_takeoff_position": None,
                "speed_mps": speed_mps,
                "heading_deg": heading_deg,
                "height_m": height_m,
                "authentication_state": authentication_state,
            },
            "extensions": {
                "decoder": payload.get("decoder", "opendroneid"),
                "raw_identifier_minimized": bool(uas_id),
            },
        },
        "privacy": {
            "class": "OPERATIONAL_MINIMIZED",
            "raw_retained": False,
            "public_export_allowed": False,
            "rotation_epoch": rotation_epoch,
        },
        "provenance": {
            "adapter_source_ref": RECEIVER_URL,
            "adapter_commit_or_version": upstream_receiver_revision,
            "raw_input_digest": operational_digest,
            "normalizer_version": ADAPTER_VERSION,
            "ingested_at_utc": ingested_at_utc,
            "raw_capture_ref": None,
        },
    }
    return finalize_observation(observation)
