"""Adapter for the pinned Flock-You JSON stream.

Flock-You remains an external sensor. Its tier/method fields are preserved as
upstream assertions because the documented JSON does not carry the packet or IE
vector needed for host-side reproduction of the match.
"""

from __future__ import annotations

import re
import math
from typing import Any

from ..canonical import rotating_identifier
from .common import finalize_observation, raw_digest

UPSTREAM_URL = "https://github.com/colonelpanichacks/flock-you"
UPSTREAM_COMMIT = "7e969663eade07833603bad86cb156338e895583"
ADAPTER_VERSION = "0.1.0"
_MAC = re.compile(r"^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")
_METHOD_TIERS = {
    "wifi_wildcard_probe_ie_sig": {4},
    "wifi_wildcard_probe": {3},
    "wifi_oui_addr2": {2},
    "wifi_oui_addr1": {1},
    "wifi_oui_addr3": {1},
    "wifi_ssid": {0},
}


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
    measurement_lineage_id: str | None = None,
    upstream_build_ref: str = UPSTREAM_COMMIT,
) -> dict[str, Any]:
    if payload.get("event") != "detection":
        raise ValueError("Flock-You adapter accepts only detection events")
    mac = str(payload.get("mac_address", ""))
    if not _MAC.fullmatch(mac):
        raise ValueError("missing or malformed source address")
    if payload.get("protocol") != "wifi_2_4ghz":
        raise ValueError("pinned adapter is verified only for wifi_2_4ghz")
    tier = payload.get("detection_tier")
    if not isinstance(tier, int) or isinstance(tier, bool) or not 0 <= tier <= 4:
        raise ValueError("invalid upstream detection tier")
    method = payload.get("detection_method")
    if method not in _METHOD_TIERS or tier not in _METHOD_TIERS[method]:
        raise ValueError("impossible upstream detection method/tier combination")
    channel = payload.get("channel")
    frequency_mhz = payload.get("frequency")
    if channel not in (1, 6, 11):
        raise ValueError("channel is outside the pinned firmware scan profile")
    if not isinstance(frequency_mhz, int):
        raise ValueError("frequency must be an integer MHz value")
    expected_frequency = {1: 2412, 6: 2437, 11: 2462}[channel]
    if frequency_mhz != expected_frequency:
        raise ValueError("channel and center frequency are inconsistent")
    rssi = payload.get("rssi")
    if isinstance(rssi, bool) or not isinstance(rssi, (int, float)) or not math.isfinite(rssi):
        raise ValueError("RSSI must be a finite number")
    if not -127 <= rssi <= 0:
        raise ValueError("RSSI is outside the accepted dBm range")
    upstream_prefix = mac[:8].lower()
    supplied_prefix = payload.get("oui")
    if supplied_prefix is not None and str(supplied_prefix).lower() != upstream_prefix:
        raise ValueError("reported prefix contradicts the source address")
    emitter_key = rotating_identifier(rotation_secret, rotation_epoch, mac)
    observation = {
        "schema_version": "1.0.0",
        "observed_at_utc": observed_at_utc,
        "clock_uncertainty_ms": clock_uncertainty_ms,
        "timing": {
            "host_received_at_utc": ingested_at_utc,
            "host_monotonic_ns": host_monotonic_ns,
            "sensor_boot_id": sensor_boot_id,
            "source_sequence": source_sequence,
            "source_time_state": "HOST_RECEIPT_ONLY",
            "clock_epoch_id": clock_epoch_id,
        },
        "measurement_lineage_id": (
            measurement_lineage_id or f"receiver:{receiver_id}:flock-you:{rotation_epoch}"
        ),
        "receiver": {
            "receiver_id": receiver_id,
            "pose_ref": pose_ref,
            "calibration_profile_id": None,
        },
        "sensor": {
            "adapter_id": "flock_you_json",
            "adapter_version": ADAPTER_VERSION,
            "hardware_profile_id": hardware_profile_id,
            "protocol": "WIFI_80211",
            "band": "2.4_GHZ",
            "channel": channel,
            "center_frequency_hz": frequency_mhz * 1_000_000,
            "bandwidth_hz": None,
            "capabilities": ["PASSIVE_WIFI_MANAGEMENT_RECEPTION", "RSSI"],
        },
        "emitter": {
            "ephemeral_emitter_key": emitter_key,
            "target_identifier": None,
            "identifier_type": "IEEE_802_MAC",
            "identifier_retention": "ROTATING_HASH",
            "address_randomization_state": (
                "LOCALLY_ADMINISTERED" if int(mac.split(":")[0], 16) & 0x02 else "GLOBALLY_ADMINISTERED"
            ),
        },
        "measurement": {
            "kind": "WIFI_DETECTION",
            "rssi_dbm": float(rssi),
            "snr_db": None,
            "frame_type": None,
            "detection_method": method,
            "upstream_tier": tier,
            "feature_hashes": [],
            "payload_digest": None,
            "bearing_deg": None,
            "bearing_uncertainty_deg": None,
            "tdoa_seconds": None,
            "tdoa_uncertainty_seconds": None,
            "remote_id": None,
            "extensions": {
                "upstream_assertion": {
                    "method": method,
                    "tier": tier,
                    "observed_prefix": upstream_prefix,
                },
                "unavailable_for_host_reproduction": [
                    "source_timestamp",
                    "packet_bytes",
                    "information_element_vector",
                    "frame_sequence_number",
                    "channel_scan_coverage",
                ],
            },
        },
        "privacy": {
            "class": "OPERATIONAL_MINIMIZED",
            "raw_retained": False,
            "public_export_allowed": False,
            "rotation_epoch": rotation_epoch,
        },
        "provenance": {
            "adapter_source_ref": UPSTREAM_URL,
            "adapter_commit_or_version": upstream_build_ref,
            "raw_input_digest": raw_digest(payload, secret=rotation_secret, rotation_epoch=rotation_epoch),
            "normalizer_version": ADAPTER_VERSION,
            "ingested_at_utc": ingested_at_utc,
            "raw_capture_ref": None,
        },
    }
    return finalize_observation(observation)
