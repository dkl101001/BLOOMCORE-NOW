"""Live receive-only Flock-You reality loop.

The live loop binds an external Flock-You USB/NDJSON feed to local observer pose,
normalizes detections, evaluates a versioned signature, and turns bounded
real-world detector misses into recursive discovery campaigns.

A miss never means "the target is absent".  When the upstream feed cannot prove
scan completeness, the generated coverage record is PARTIAL and the campaign is
advanced to SENSING_APERTURE_INSUFFICIENT so the next observation cycle must
widen or improve the aperture.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import queue
import stat
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO

from . import CODE_REVISION, runtime_source_digest
from .adapters.flock_you import normalize
from .canonical import content_id, keyed_content_id, keyed_digest, sha256_uri
from .ledger import EvidenceLedger
from .recursive import advance_campaign, make_failure_packet, open_discovery_campaign
from .replay import _association, _item_ref, _make_pass_partition, make_pose
from .inference import Sample, localize_static
from .receipts import make_receipt
from .signatures import evaluate

EARTH_RADIUS_M = 6_371_008.8
MAX_LINE_BYTES = 1_048_576


def _utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def _instant(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must carry a UTC offset")
    return parsed.astimezone(dt.UTC)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    a1, a2 = math.radians(lat1), math.radians(lat2)
    dlat = a2 - a1
    dlon = math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(a1) * math.cos(a2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def signature_ref(signature: dict[str, Any]) -> str:
    return f"{signature['signature_id']}@{signature['version']}"


@dataclass(frozen=True)
class TargetExpectation:
    target_asset_ref: str
    signature_ref: str
    latitude: float
    longitude: float
    trigger_radius_m: float
    exit_radius_m: float
    target_evidence_refs: tuple[str, ...]
    failed_assumption: str
    next_tests: tuple[str, ...]
    minimum_pose_count: int = 2
    cooldown_seconds: float = 60.0

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TargetExpectation":
        trigger = float(value["trigger_radius_m"])
        exit_radius = float(value["exit_radius_m"])
        if trigger <= 0 or exit_radius <= 0:
            raise ValueError("target radii must be positive")
        if exit_radius < trigger:
            raise ValueError("exit_radius_m must be >= trigger_radius_m to prevent edge chatter")
        evidence_refs = tuple(str(item) for item in value["target_evidence_refs"] if str(item).strip())
        if not evidence_refs:
            raise ValueError("target expectation requires independent target evidence references")
        tests = tuple(str(item) for item in value["next_tests"] if str(item).strip())
        if not tests:
            raise ValueError("target expectation requires at least one next test")
        minimum_pose_count = int(value.get("minimum_pose_count", 2))
        if minimum_pose_count < 2:
            raise ValueError("minimum_pose_count must be at least two")
        return cls(
            target_asset_ref=str(value["target_asset_ref"]),
            signature_ref=str(value["signature_ref"]),
            latitude=float(value["latitude"]),
            longitude=float(value["longitude"]),
            trigger_radius_m=trigger,
            exit_radius_m=exit_radius,
            target_evidence_refs=evidence_refs,
            failed_assumption=str(value["failed_assumption"]),
            next_tests=tests,
            minimum_pose_count=minimum_pose_count,
            cooldown_seconds=float(value.get("cooldown_seconds", 60.0)),
        )


@dataclass
class _Window:
    expectation: TargetExpectation
    opened_at_utc: str
    pose_refs: list[str] = field(default_factory=list)
    match_refs: list[str] = field(default_factory=list)
    observation_refs: list[str] = field(default_factory=list)
    closest_distance_m: float = math.inf
    sensor_event_count_at_open: int = 0
    quarantined_count_at_open: int = 0


class LiveRealityLoop:
    """Stateful receive-only live loop with recursive miss generation."""

    def __init__(
        self,
        *,
        signature: dict[str, Any],
        expectations: list[TargetExpectation],
        receiver_id: str,
        hardware_profile_id: str,
        rotation_epoch: str,
        rotation_secret: bytes,
        ledger: EvidenceLedger | None = None,
        max_pose_age_seconds: float = 3.0,
        upstream_build_ref: str = "UNVERIFIED_LIVE_FEED",
        session_id: str | None = None,
    ):
        if len(rotation_secret) < 32:
            raise ValueError("rotation secret must be at least 32 bytes")
        if max_pose_age_seconds <= 0:
            raise ValueError("max_pose_age_seconds must be positive")
        self.signature = signature
        self.expected_signature_ref = signature_ref(signature)
        for expectation in expectations:
            if expectation.signature_ref != self.expected_signature_ref:
                raise ValueError(
                    f"target {expectation.target_asset_ref} expects {expectation.signature_ref}, "
                    f"but loaded signature is {self.expected_signature_ref}"
                )
        self.expectations = expectations
        self.receiver_id = receiver_id
        self.hardware_profile_id = hardware_profile_id
        self.rotation_epoch = rotation_epoch
        self.rotation_secret = rotation_secret
        self.ledger = ledger
        self.max_pose_age_seconds = float(max_pose_age_seconds)
        self.upstream_build_ref = upstream_build_ref
        self.session_id = session_id or content_id(
            "live", {"receiver_id": receiver_id, "rotation_epoch": rotation_epoch}, 32
        )
        self.latest_pose: dict[str, Any] | None = None
        self.latest_pass_id = "live-pass-1"
        self.emitter_groups: dict[str, dict[str, Any]] = {}
        self.node_state: dict[str, dict[str, Any]] = {}
        self.windows: dict[str, _Window] = {}
        self.cooldown_until: dict[str, dt.datetime] = {}
        self.sensor_connected = False
        self.sensor_message_count = 0
        self.accepted_detection_count = 0
        self.quarantined_count = 0
        self.last_sensor_message_at_utc: str | None = None
        self._lineage_id = keyed_content_id(
            "mlineage",
            rotation_secret,
            {
                "session_id": self.session_id,
                "receiver_id": receiver_id,
                "adapter": "flock_you_json_live",
            },
            40,
        )
        self._lineage_persisted = False

    def mark_sensor_connected(self, observed_at_utc: str | None = None) -> None:
        self.sensor_connected = True
        self.last_sensor_message_at_utc = observed_at_utc or _utc_now()

    def mark_sensor_disconnected(self) -> None:
        self.sensor_connected = False

    def mark_quarantined(self) -> None:
        self.quarantined_count += 1

    def _persist_lineage(self) -> dict[str, Any]:
        core = {
            "schema_version": "1.0.0",
            "measurement_lineage_id": self._lineage_id,
            "raw_capture_digest": None,
            "session_id": self.session_id,
            "pass_id": None,
            "receiver_id": self.receiver_id,
            "calibration_profile_id": None,
            "normalization_transform": {
                "name": "flock_you_live_json_normalizer",
                "version": "0.2.0",
                "code_revision": CODE_REVISION,
                "code_digest": runtime_source_digest(),
            },
            "parent_lineage_ids": [],
        }
        lineage = {**core, "content_hash": sha256_uri(core)}
        if self.ledger is not None and not self._lineage_persisted:
            self.ledger.append_event(
                "measurement_lineage", lineage["measurement_lineage_id"], lineage
            )
            self._lineage_persisted = True
        return lineage

    def ingest_pose(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        """Ingest one local GNSS/pose record and close target windows on exit."""

        if record.get("receiver_id", self.receiver_id) != self.receiver_id:
            raise ValueError("pose receiver_id does not match live receiver")
        pose_seed = {
            **record,
            "receiver_id": self.receiver_id,
            "source": record.get("source", "GNSS"),
        }
        pose = make_pose(pose_seed, id_secret=self.rotation_secret)
        self.latest_pose = pose
        self.latest_pass_id = str(record.get("pass_id", self.latest_pass_id or "live-pass-1"))
        if not self.latest_pass_id:
            raise ValueError("pass_id cannot be empty")
        if self.ledger is not None:
            self.ledger.append_restricted_pose(pose)

        now = _instant(pose["observed_at_utc"])
        generated: list[dict[str, Any]] = []
        lat = float(pose["position"]["latitude"])
        lon = float(pose["position"]["longitude"])
        for expectation in self.expectations:
            distance = _haversine_m(lat, lon, expectation.latitude, expectation.longitude)
            window = self.windows.get(expectation.target_asset_ref)
            cooldown = self.cooldown_until.get(expectation.target_asset_ref)
            if window is None:
                if cooldown is not None and now < cooldown:
                    continue
                if distance <= expectation.trigger_radius_m:
                    self.windows[expectation.target_asset_ref] = _Window(
                        expectation=expectation,
                        opened_at_utc=pose["observed_at_utc"],
                        pose_refs=[pose["pose_id"]],
                        closest_distance_m=distance,
                        sensor_event_count_at_open=self.sensor_message_count,
                        quarantined_count_at_open=self.quarantined_count,
                    )
                continue
            window.closest_distance_m = min(window.closest_distance_m, distance)
            if pose["pose_id"] not in window.pose_refs:
                window.pose_refs.append(pose["pose_id"])
            if distance > expectation.exit_radius_m:
                generated.extend(self._finalize_window(window, pose["observed_at_utc"]))
                del self.windows[expectation.target_asset_ref]
                self.cooldown_until[expectation.target_asset_ref] = now + dt.timedelta(
                    seconds=expectation.cooldown_seconds
                )
        return generated

    def ingest_flock_you(self, payload: dict[str, Any], *, received_at_utc: str | None = None,
                         host_monotonic_ns: int | None = None) -> list[dict[str, Any]]:
        """Normalize one upstream Flock-You event.

        Config messages prove only that a host message was received.  They do not
        prove scan completeness and therefore never support an absence claim.
        """

        received = received_at_utc or _utc_now()
        self.sensor_connected = True
        self.sensor_message_count += 1
        self.last_sensor_message_at_utc = received
        if payload.get("event") == "config":
            return [{
                "kind": "sensor_config_seen",
                "observed_at_utc": received,
                "upstream_build_ref": self.upstream_build_ref,
            }]
        if payload.get("event") != "detection":
            raise ValueError(f"unsupported Flock-You event {payload.get('event')!r}")

        pose = self.latest_pose
        pose_ref = None
        if pose is not None:
            age = abs((_instant(received) - _instant(pose["observed_at_utc"])).total_seconds())
            if age <= self.max_pose_age_seconds:
                pose_ref = pose["pose_id"]
        self._persist_lineage()
        observation = normalize(
            payload,
            observed_at_utc=received,
            ingested_at_utc=received,
            receiver_id=self.receiver_id,
            hardware_profile_id=self.hardware_profile_id,
            rotation_epoch=self.rotation_epoch,
            rotation_secret=self.rotation_secret,
            pose_ref=pose_ref,
            clock_uncertainty_ms=1000.0,
            host_monotonic_ns=host_monotonic_ns,
            sensor_boot_id=None,
            source_sequence=None,
            measurement_lineage_id=self._lineage_id,
            upstream_build_ref=self.upstream_build_ref,
        )
        match = evaluate(observation, self.signature)
        self.accepted_detection_count += 1
        generated = [
            {"kind": "observation", "value": observation},
            {"kind": "signature_match", "value": match},
        ]
        if self.ledger is not None:
            self.ledger.append_event("observation", observation["observation_id"], observation)
            self.ledger.append_event("signature_match", match["match_id"], match)

        if match["match_state"] == "MATCH":
            generated.append({
                "kind": "local_alert",
                "alert": "COMPATIBLE_FLOCK_YOU_SIGNATURE",
                "match_ref": match["match_id"],
                "claim_ceiling": match["claim_ceiling"],
                "probability": None,
            })

        if pose_ref is not None and pose is not None:
            association, association_receipt = _association(
                observation, pose,
                max_pose_offset_ms=self.max_pose_age_seconds * 1000.0
                    + float(observation["clock_uncertainty_ms"])
                    + float(pose["clock_uncertainty_ms"]),
                rotation_secret=self.rotation_secret, code_digest=runtime_source_digest(),
            )
            if self.ledger is not None:
                self.ledger.append_event("pose_association", association["association_id"], association)
                self.ledger.append_event("evidence_receipt", association_receipt["receipt_id"], association_receipt)
            generated.extend([
                {"kind": "pose_association", "value": association},
                {"kind": "evidence_receipt", "value": association_receipt},
            ])
            emitter_key = observation["emitter"]["ephemeral_emitter_key"]
            if emitter_key:
                group = self.emitter_groups.setdefault(emitter_key, {
                    "observations": [], "matches": [], "associations": [],
                    "association_receipts": [], "poses": {}, "samples": [], "pass_map": {},
                })
                group["observations"].append(observation)
                group["matches"].append(match)
                group["associations"].append(association)
                group["association_receipts"].append(association_receipt)
                group["poses"][pose["pose_id"]] = pose
                group["pass_map"][observation["observation_id"]] = self.latest_pass_id
                group["samples"].append(Sample(
                    latitude=float(pose["position"]["latitude"]),
                    longitude=float(pose["position"]["longitude"]),
                    rssi_dbm=float(observation["measurement"]["rssi_dbm"]),
                    receiver_id=self.receiver_id,
                    pass_id=self.latest_pass_id,
                    horizontal_accuracy_m=float(pose["position"]["horizontal_accuracy_m"]),
                ))
                generated.extend(self._maybe_build_live_node(emitter_key, received))

        if pose_ref is not None:
            for window in self.windows.values():
                if pose_ref in window.pose_refs:
                    window.observation_refs.append(observation["observation_id"])
                    if match["match_state"] == "MATCH":
                        window.match_refs.append(match["match_id"])
        return generated

    def _maybe_build_live_node(self, emitter_key: str, observed_at_utc: str) -> list[dict[str, Any]]:
        """Build/update a private local node after two explicit passes provide geometry."""

        group = self.emitter_groups[emitter_key]
        if len(group["samples"]) < 4 or len(set(group["pass_map"].values())) < 2:
            return []
        try:
            spatial = localize_static(group["samples"] )
        except (ValueError, RuntimeError):
            return []
        lineage = self._persist_lineage()
        partition = _make_pass_partition(
            group["pass_map"], session_id=self.session_id, code_digest=runtime_source_digest()
        )
        if self.ledger is not None:
            self.ledger.append_event("pass_partition", partition["partition_id"], partition)

        source_locks = [{
            "source_id": "https://github.com/colonelpanichacks/flock-you",
            "revision": self.upstream_build_ref,
            "content_hash": None,
        }]
        spatial_inputs = (
            group["observations"] + group["matches"] + list(group["poses"].values())
            + group["associations"] + group["association_receipts"] + [lineage, partition]
        )
        refs: list[str] = []
        hashes: list[str] = []
        for item in spatial_inputs:
            if "pose_id" in item:
                refs.append(item["pose_id"] )
                hashes.append(keyed_digest(
                    self.rotation_secret, "restricted-pose-receipt", item
                ))
            else:
                refs.append(_item_ref(item))
                hashes.append(sha256_uri(item))
        spatial_receipt = make_receipt(
            subject_ref=f"static-rf-support-region:{emitter_key}",
            input_refs=refs, input_hashes=hashes,
            algorithm_name="rank_rssi_support_grid",
            algorithm_version=spatial["diagnostics"]["algorithm_version"],
            parameters={
                "requested_grid_step_m": 10.0,
                "actual_grid_step_m": spatial["diagnostics"]["grid_step_m"],
                "requested_margin_m": 120.0,
                "maximum_pose_accuracy_m": spatial["diagnostics"]["max_pose_accuracy_m"],
                "duplicate_control": "median_by_receiver_pass_rounded_pose",
                "rank_minimum_rssi_delta_db": 3.0,
                "score_tolerance_floor": 1.0,
                "score_tolerance_fraction": 0.08,
                "grid_cell_cap": 50000,
                "local_plane_max_span_deg": spatial["diagnostics"]["local_plane_max_span_deg"],
                "cross_receiver_comparisons": False,
                "calibration_state": "UNCALIBRATED",
                "live_mode": True,
            },
            output=spatial, source_locks=source_locks,
            code_revision=CODE_REVISION, code_digest=runtime_source_digest(),
        )
        if self.ledger is not None:
            self.ledger.append_event("evidence_receipt", spatial_receipt["receipt_id"], spatial_receipt)

        node_id = content_id("node", {
            "measurement_lineages": [self._lineage_id], "emitter_key": emitter_key,
        }, 32)
        previous = self.node_state.get(emitter_key)
        revision = 1 if previous is None else int(previous["revision"]) + 1
        matched = any(item["match_state"] == "MATCH" for item in group["matches"] )
        evidence_refs = sorted(
            [item["observation_id"] for item in group["observations"]]
            + [item["match_id"] for item in group["matches"]]
            + [item["association_id"] for item in group["associations"]]
            + [item["receipt_id"] for item in group["association_receipts"]]
            + [self._lineage_id, partition["partition_id"], spatial_receipt["receipt_id"]]
        )
        node_body = {
            "schema_version": "1.0.0",
            "node_id": node_id,
            "revision": revision,
            "parent_revision_hash": None if previous is None else previous["ledger_hash"],
            "motion_state": "MOTION_UNRESOLVED",
            "asset_kind_hypotheses": ["UNKNOWN"],
            "evidence_state": "MEASURED",
            "lifecycle_state": "CANDIDATE",
            "claim_level": "SIGNATURE_MATCH" if matched else "RF_ACTIVITY_PRESENT",
            "classification": {
                "ranked_labels": ["RF_PATTERN", "UNKNOWN"] if matched else ["UNKNOWN"],
                "probabilities": None, "calibration_state": "UNCALIBRATED",
                "confidence_label": "UNKNOWN",
            },
            "location": {key: value for key, value in spatial.items() if key != "diagnostics"},
            "trajectory": None,
            "evidence_refs": evidence_refs,
            "independent_source_lineages": [],
            "measurement_lineages": [self._lineage_id],
            "contradiction_refs": [],
            "updated_at_utc": observed_at_utc,
            "publication_state": "PRIVATE_LOCAL",
        }
        node_inputs = (
            group["observations"] + group["matches"] + group["associations"]
            + group["association_receipts"] + [lineage, partition, spatial_receipt]
        )
        node_input_refs = [_item_ref(item) for item in node_inputs]
        node_input_hashes = [sha256_uri(item) for item in node_inputs]
        if previous is not None:
            node_input_refs.append(f"{node_id}:revision:{revision - 1}")
            node_input_hashes.append(previous["ledger_hash"] )
        node_receipt = make_receipt(
            subject_ref=f"{node_id}:revision:{revision}",
            input_refs=node_input_refs, input_hashes=node_input_hashes,
            algorithm_name="node_revision_assembler", algorithm_version="1.0.0",
            parameters={
                "claim_ceiling_policy": "candidate-rf-pattern-v1",
                "motion_default": "MOTION_UNRESOLVED",
                "calibration_required_for_probability": True,
                "emitter_partition": "ephemeral_emitter_key",
                "live_mode": True,
            },
            output=node_body, source_locks=source_locks,
            code_revision=CODE_REVISION, code_digest=runtime_source_digest(),
        )
        node = {**node_body, "receipt_id": node_receipt["receipt_id"]}
        if self.ledger is not None:
            self.ledger.append_event("evidence_receipt", node_receipt["receipt_id"], node_receipt)
            ledger_hash = self.ledger.append_node_revision(node)
        else:
            ledger_hash = sha256_uri(node)
        self.node_state[emitter_key] = {"revision": revision, "ledger_hash": ledger_hash}
        return [
            {"kind": "pass_partition", "value": partition},
            {"kind": "spatial_result", "value": spatial},
            {"kind": "evidence_receipt", "value": spatial_receipt},
            {"kind": "node_revision", "value": node},
            {"kind": "evidence_receipt", "value": node_receipt},
        ]

    def flush(self, observed_at_utc: str | None = None) -> list[dict[str, Any]]:
        """Close all open target windows, e.g. on sensor shutdown or session end."""

        when = observed_at_utc or _utc_now()
        generated: list[dict[str, Any]] = []
        for asset_ref in list(self.windows):
            generated.extend(self._finalize_window(self.windows[asset_ref], when))
            del self.windows[asset_ref]
        return generated

    def _coverage_event(self, window: _Window, closed_at_utc: str) -> dict[str, Any]:
        messages = self.sensor_message_count - window.sensor_event_count_at_open
        quarantined = self.quarantined_count - window.quarantined_count_at_open
        if not self.sensor_connected:
            state = "LOSS_GAP"
        elif messages == 0:
            state = "PARTIAL"
        else:
            state = "PARTIAL"
        limitations = [
            "UPSTREAM_FLOCK_YOU_JSON_DOES_NOT_REPORT_CHANNEL_SCAN_COMPLETENESS",
            "SERIAL_OR_STREAM_CONTINUITY_IS_NOT_PROOF_OF_RF_COVERAGE",
            "CURRENT_RECEIVER_PROFILE_IS_2_4_GHZ_ONLY",
        ]
        if quarantined:
            limitations.append("QUARANTINED_INPUT_OCCURRED_DURING_TARGET_WINDOW")
        if messages == 0:
            limitations.append("NO_UPSTREAM_MESSAGE_WAS_OBSERVED_DURING_TARGET_WINDOW")
        core = {
            "schema_version": "1.0.0",
            "receiver_id": self.receiver_id,
            "hardware_profile_id": self.hardware_profile_id,
            "started_at_utc": window.opened_at_utc,
            "ended_at_utc": closed_at_utc,
            "protocols": ["WIFI_80211"],
            "bands": ["2.4_GHZ"],
            "channels": [1, 6, 11],
            "state": state,
            "loss_count": quarantined,
            "limitations": limitations,
        }
        coverage = {**core, "coverage_id": content_id("coverage", core, 40)}
        coverage["content_hash"] = sha256_uri(coverage)
        if self.ledger is not None:
            self.ledger.append_event("sensor_coverage", coverage["coverage_id"], coverage)
        return coverage

    def _finalize_window(self, window: _Window, closed_at_utc: str) -> list[dict[str, Any]]:
        expectation = window.expectation
        if len(window.pose_refs) < expectation.minimum_pose_count:
            return [{
                "kind": "target_window_discarded",
                "target_asset_ref": expectation.target_asset_ref,
                "reason": "INSUFFICIENT_POSE_SAMPLES",
                "pose_count": len(window.pose_refs),
            }]
        if window.match_refs:
            return [{
                "kind": "target_window_match",
                "target_asset_ref": expectation.target_asset_ref,
                "signature_ref": expectation.signature_ref,
                "target_evidence_refs": list(expectation.target_evidence_refs),
                "match_refs": list(dict.fromkeys(window.match_refs)),
                "observation_refs": list(dict.fromkeys(window.observation_refs)),
                "closest_distance_m": round(window.closest_distance_m, 2),
                "claim": "COMPATIBLE_SIGNATURE_OBSERVED_IN_TARGET_WINDOW",
                "target_identity_proven": False,
            }]

        coverage = self._coverage_event(window, closed_at_utc)
        failure = make_failure_packet(
            target_asset_ref=expectation.target_asset_ref,
            failed_expectation=f"compatible live signature {expectation.signature_ref} during bounded target traversal",
            observation_refs=list(dict.fromkeys(window.observation_refs)),
            coverage_refs=[coverage["coverage_id"]],
            context_refs=[*window.pose_refs, *expectation.target_evidence_refs],
            failed_assumption=expectation.failed_assumption,
            rationale=(
                "No compatible signature was captured while the observer traversed the bounded target region. "
                "The current upstream feed does not expose channel-scan completeness, so this is evidence of a "
                "detector miss under the present aperture, never evidence that the target or its emissions are absent."
            ),
            next_test_seed=expectation.next_tests[0],
            observed_at_utc=closed_at_utc,
        )
        campaign = open_discovery_campaign(
            failure,
            next_tests=list(expectation.next_tests),
            opened_at_utc=closed_at_utc,
        )
        if self.ledger is not None:
            self.ledger.append_event("failure_packet", failure["failure_id"], failure)
            self.ledger.append_discovery_campaign_revision(campaign)

        campaign = advance_campaign(
            campaign,
            new_state="SENSING_APERTURE_INSUFFICIENT",
            evidence_refs=[coverage["coverage_id"], *window.pose_refs],
            next_tests=list(expectation.next_tests),
            updated_at_utc=closed_at_utc,
            missing_features=[
                f"validated passive discriminator for {expectation.target_asset_ref}",
                "verified scan-completeness telemetry for the current receive aperture",
            ],
            claim_ceiling="RF_ACTIVITY_PRESENT",
        )
        if self.ledger is not None:
            self.ledger.append_discovery_campaign_revision(campaign)
        return [
            {"kind": "sensor_coverage", "value": coverage},
            {"kind": "failure_packet", "value": failure},
            {"kind": "discovery_campaign", "value": campaign},
        ]


class _LineReader(threading.Thread):
    """Read bounded NDJSON lines from stdin, a file/FIFO, or a USB CDC TTY."""

    def __init__(self, name: str, path: str, out: queue.Queue[tuple[str, str | None, Exception | None]], *,
                 baud: int | None = None):
        super().__init__(name=f"flockoff-{name}-reader", daemon=True)
        self.source_name = name
        self.path = path
        self.out = out
        self.baud = baud

    @staticmethod
    def _configure_tty(fd: int, baud: int) -> None:
        if os.name != "posix":
            return
        import termios
        attrs = termios.tcgetattr(fd)
        speed_name = f"B{baud}"
        if not hasattr(termios, speed_name):
            raise ValueError(f"unsupported POSIX serial baud {baud}")
        speed = getattr(termios, speed_name)
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = (attrs[2] | termios.CLOCAL | termios.CREAD | termios.CS8) & ~termios.PARENB
        attrs[3] = 0
        attrs[4] = speed
        attrs[5] = speed
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = 10
        termios.tcsetattr(fd, termios.TCSANOW, attrs)

    def run(self) -> None:
        try:
            if self.path == "-":
                for line in sys.stdin:
                    self._emit(line)
                self.out.put((self.source_name, None, None))
                return
            fd = os.open(self.path, os.O_RDONLY | getattr(os, "O_NOCTTY", 0))
            mode = os.fstat(fd).st_mode
            if stat.S_ISCHR(mode) and self.baud is not None:
                self._configure_tty(fd, self.baud)
            buffer = bytearray()
            try:
                while True:
                    chunk = os.read(fd, 4096)
                    if not chunk:
                        if stat.S_ISREG(mode):
                            break
                        time.sleep(0.05)
                        continue
                    buffer.extend(chunk)
                    if len(buffer) > MAX_LINE_BYTES and b"\n" not in buffer:
                        raise ValueError(f"{self.source_name} NDJSON line exceeds 1 MiB")
                    while b"\n" in buffer:
                        raw, _, rest = buffer.partition(b"\n")
                        buffer = bytearray(rest)
                        self._emit(raw.decode("utf-8", errors="strict"))
                if buffer.strip():
                    self._emit(buffer.decode("utf-8", errors="strict"))
            finally:
                os.close(fd)
            self.out.put((self.source_name, None, None))
        except Exception as exc:  # surfaced to the main thread
            self.out.put((self.source_name, None, exc))

    def _emit(self, line: str) -> None:
        if len(line.encode("utf-8")) > MAX_LINE_BYTES:
            raise ValueError(f"{self.source_name} NDJSON line exceeds 1 MiB")
        if line.strip():
            self.out.put((self.source_name, line, None))


def iter_named_sources(*, sensor_name: str, sensor_path: str, pose_path: str | None,
                       baud: int = 115200):
    """Yield a named receive-only sensor stream plus a separate pose stream."""

    if not sensor_name or sensor_name == "pose":
        raise ValueError("sensor_name must be nonempty and distinct from pose")
    items: queue.Queue[tuple[str, str | None, Exception | None]] = queue.Queue()
    readers = [_LineReader(sensor_name, sensor_path, items, baud=baud)]
    if pose_path is not None:
        if pose_path == "-" and sensor_path == "-":
            raise ValueError("sensor and pose sources cannot both consume stdin")
        readers.append(_LineReader("pose", pose_path, items))
    for reader in readers:
        reader.start()
    ended: set[str] = set()
    while len(ended) < len(readers):
        source, line, error = items.get()
        if error is not None:
            raise error
        if line is None:
            ended.add(source)
            continue
        yield source, line


def iter_live_sources(*, flock_you_path: str, pose_path: str | None, baud: int = 115200):
    """Backward-compatible v0.2 Flock-You source multiplexer."""

    yield from iter_named_sources(
        sensor_name="flock_you", sensor_path=flock_you_path,
        pose_path=pose_path, baud=baud,
    )


def strict_json_object(line: str) -> dict[str, Any]:
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    value = json.loads(
        line,
        object_pairs_hook=hook,
        parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
    )
    if not isinstance(value, dict):
        raise ValueError("live NDJSON records must be JSON objects")
    return value
