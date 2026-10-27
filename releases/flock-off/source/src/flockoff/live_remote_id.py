"""Live receive-only Remote ID observation loop.

Radio reception and protocol decoding stay behind an external, pinned adapter.
This module consumes decoded NDJSON, preserves observer pose separately from
emitter-reported position, and creates immutable mobile-track, node, alert, and
receipt evidence. It contains no networking, radio transmission, connection,
or device-control capability.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from . import CODE_REVISION, runtime_source_digest
from .adapters.remote_id import (
    ADAPTER_VERSION,
    CORE_REVISION,
    CORE_URL,
    RECEIVER_RELEASE,
    RECEIVER_REVISION,
    RECEIVER_URL,
    STANDARD_PROFILE_REF,
    normalize,
)
from .canonical import content_id, keyed_content_id, keyed_digest, sha256_uri, without_keys
from .ledger import EvidenceLedger
from .mobile import MobileTrack, TrackPoint
from .receipts import make_receipt
from .replay import _association, make_pose


def _utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def _instant(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must carry a UTC offset")
    return parsed.astimezone(dt.UTC)


def _source_locks(receiver_revision: str, core_revision: str) -> list[dict[str, Any]]:
    return [
        {
            "source_id": RECEIVER_URL,
            "revision": receiver_revision,
            "content_hash": None,
        },
        {
            "source_id": CORE_URL,
            "revision": core_revision,
            "content_hash": None,
        },
        {
            "source_id": "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-89",
            "revision": "accessed-2026-08-23",
            "content_hash": None,
        },
    ]


def _message_type(payload: dict[str, Any]) -> str:
    value = str(payload.get("message_type", "MESSAGE_PACK")).upper()
    allowed = {
        "BASIC_ID", "LOCATION_VECTOR", "SYSTEM", "SELF_ID", "OPERATOR_ID",
        "AUTHENTICATION", "MESSAGE_PACK", "UNKNOWN",
    }
    if value not in allowed:
        raise ValueError("unsupported Remote ID message_type")
    return value


def make_remote_id_message(
    payload: dict[str, Any], observation: dict[str, Any], *,
    receiver_revision: str, core_revision: str,
) -> dict[str, Any]:
    """Create a typed event from a decoded upstream record without retaining raw IDs."""

    remote = observation["measurement"]["remote_id"]
    validity = remote["validity"]
    position = remote["aircraft_position"]
    if position is not None:
        position = {
            **position,
            "altitude_reference": str(payload.get("altitude_reference", "UNKNOWN")).upper(),
            "vertical_accuracy_m": payload.get("vertical_accuracy_m"),
        }
        if position["altitude_reference"] not in {"WGS84", "MSL", "AGL", "UNKNOWN"}:
            raise ValueError("invalid Remote ID altitude reference")
    semantic = {
        "VALID": "VALID",
        "UNVERIFIED": "NOT_EVALUATED",
        "INCOMPLETE": "INCOMPLETE",
        "MALFORMED": "NOT_EVALUATED",
        "CONTRADICTED": "CONTRADICTED",
    }[validity]
    syntax = "MALFORMED" if validity == "MALFORMED" else "VALID"
    authentication = remote["authentication_state"]
    core = {
        "schema_version": "1.0.0",
        "implementation_state": "IMPLEMENTED_DECODED_UPSTREAM",
        "observation_ref": observation["observation_id"],
        "message_type": _message_type(payload),
        "transport": remote["transport"],
        "received_at_utc": observation["timing"]["host_received_at_utc"],
        "clock_uncertainty_ms": observation["clock_uncertainty_ms"],
        "receiver_ref": observation["receiver"]["receiver_id"],
        "hardware_profile_id": observation["sensor"]["hardware_profile_id"],
        "decoder_lock": {
            "decoder_name": "opendroneid-decoded-json-boundary",
            "decoder_version": RECEIVER_RELEASE,
            "source_ref": RECEIVER_URL,
            "source_revision": receiver_revision,
            "core_source_ref": CORE_URL,
            "core_revision": core_revision,
            "standard_profile_ref": STANDARD_PROFILE_REF,
        },
        "transport_metadata": {
            "band": observation["sensor"]["band"],
            "channel": observation["sensor"]["channel"],
            "center_frequency_hz": observation["sensor"]["center_frequency_hz"],
            "receiver_capability_ref": observation["sensor"]["hardware_profile_id"],
        },
        "syntax_state": syntax,
        "semantic_state": semantic,
        "freshness_state": str(payload.get("freshness_state", "UNKNOWN")).upper(),
        "replay_state": str(payload.get("replay_state", "UNKNOWN")).upper(),
        "authentication": {
            "present": authentication != "NOT_PRESENT",
            "verification": authentication,
            "trust_anchor_state": "NOT_APPLICABLE" if authentication == "NOT_PRESENT" else "UNKNOWN",
            "verification_receipt_id": None,
        },
        "decoded_body": {
            "uas_id_type": remote.get("uas_id_type"),
            "uas_id_rotating_hash": observation["emitter"]["ephemeral_emitter_key"],
            "aircraft_position": position,
            "speed_mps": remote.get("speed_mps"),
            "heading_deg": remote.get("heading_deg"),
            "height_m": remote.get("height_m"),
            "operator_identifier_rotating_hash": None,
            "self_id_text_digest": None,
            "authentication_page_number": payload.get("authentication_page_number"),
            "authentication_page_count": payload.get("authentication_page_count"),
        },
        "restricted_field_refs": [],
        "payload_digest": observation["measurement"]["payload_digest"],
    }
    if core["freshness_state"] not in {"FRESH", "STALE", "UNKNOWN"}:
        raise ValueError("invalid Remote ID freshness state")
    if core["replay_state"] not in {"NOT_SUSPECTED", "SUSPECTED", "UNKNOWN"}:
        raise ValueError("invalid Remote ID replay state")
    return {**core, "message_id": content_id("ridmsg", core, 40)}


class RemoteIDLiveLoop:
    """Stateful v0.3 loop for decoded live Broadcast Remote ID evidence."""

    def __init__(
        self, *, receiver_id: str, hardware_profile_id: str, rotation_epoch: str,
        rotation_secret: bytes, ledger: EvidenceLedger | None = None,
        max_pose_age_seconds: float = 3.0, max_source_clock_skew_seconds: float = 5.0,
        upstream_receiver_revision: str = RECEIVER_REVISION,
        upstream_core_revision: str = CORE_REVISION,
        session_id: str | None = None,
    ):
        if len(rotation_secret) < 32:
            raise ValueError("rotation secret must be at least 32 bytes")
        if max_pose_age_seconds <= 0 or max_source_clock_skew_seconds <= 0:
            raise ValueError("time bounds must be positive")
        self.receiver_id = receiver_id
        self.hardware_profile_id = hardware_profile_id
        self.rotation_epoch = rotation_epoch
        self.rotation_secret = rotation_secret
        self.ledger = ledger
        self.max_pose_age_seconds = float(max_pose_age_seconds)
        self.max_source_clock_skew_seconds = float(max_source_clock_skew_seconds)
        self.upstream_receiver_revision = upstream_receiver_revision
        self.upstream_core_revision = upstream_core_revision
        self.session_id = session_id or keyed_content_id(
            "ridsession", rotation_secret,
            {"receiver_id": receiver_id, "rotation_epoch": rotation_epoch}, 40,
        )
        self.latest_pose: dict[str, Any] | None = None
        self.groups: dict[str, dict[str, Any]] = {}
        self.node_state: dict[str, dict[str, Any]] = {}
        self.seen_sequences: dict[tuple[str, int], str] = {}
        self.received_count = 0
        self.accepted_count = 0
        self.duplicate_count = 0
        self.quarantined_count = 0
        self.explicitly_lost_count = 0
        self._lineage_id = keyed_content_id(
            "mlineage", rotation_secret,
            {"session_id": self.session_id, "receiver_id": receiver_id,
             "adapter": "remote_id_decoded_json_live"}, 40,
        )
        self._lineage_persisted = False

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
                "name": "remote_id_decoded_json_live_normalizer",
                "version": ADAPTER_VERSION,
                "code_revision": CODE_REVISION,
                "code_digest": runtime_source_digest(),
            },
            "parent_lineage_ids": [],
        }
        lineage = {**core, "content_hash": sha256_uri(core)}
        if self.ledger is not None and not self._lineage_persisted:
            self.ledger.append_event("measurement_lineage", self._lineage_id, lineage)
            self._lineage_persisted = True
        return lineage

    def ingest_pose(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        if record.get("receiver_id", self.receiver_id) != self.receiver_id:
            raise ValueError("pose receiver_id does not match Remote ID receiver")
        pose = make_pose(
            {**record, "receiver_id": self.receiver_id,
             "source": record.get("source", "GNSS")},
            id_secret=self.rotation_secret,
        )
        self.latest_pose = pose
        if self.ledger is not None:
            self.ledger.append_restricted_pose(pose)
        return [{"kind": "restricted_pose_accepted", "pose_ref": pose["pose_id"]}]

    def mark_quarantined(self) -> None:
        self.quarantined_count += 1

    def ingest_status(self, record: dict[str, Any], *, received_at_utc: str | None = None) -> list[dict[str, Any]]:
        received = received_at_utc or _utc_now()
        lost = int(record.get("explicitly_lost_count", 0))
        if lost < 0:
            raise ValueError("explicitly_lost_count cannot be negative")
        self.explicitly_lost_count += lost
        state = str(record.get("state", "HEALTHY")).upper()
        if state not in {
            "HEALTHY", "DEGRADED", "DISCONNECTED", "BACKPRESSURE", "DISK_FULL",
            "CLOCK_RESET", "CORRUPT_INPUT", "STOPPED",
        }:
            raise ValueError("invalid Remote ID receiver health state")
        core = {
            "schema_version": "1.0.0",
            "adapter_id": "opendroneid_decoded_json_live",
            "receiver_id": self.receiver_id,
            "observed_at_utc": received,
            "state": state,
            "received_count": self.received_count,
            "accepted_count": self.accepted_count,
            "duplicate_count": self.duplicate_count,
            "quarantined_count": self.quarantined_count,
            "explicitly_lost_count": self.explicitly_lost_count,
            "reason_codes": sorted({str(item) for item in record.get("reason_codes", [])}),
        }
        event = {**core, "health_id": content_id("health", core, 40)}
        event["content_hash"] = sha256_uri(event)
        if self.ledger is not None:
            self.ledger.append_event("adapter_health", event["health_id"], event)
        return [{"kind": "adapter_health", "value": event,
                 "absence_claim_permitted": False}]

    def ingest_remote_id(
        self, payload: dict[str, Any], *, received_at_utc: str | None = None,
        host_monotonic_ns: int | None = None,
    ) -> list[dict[str, Any]]:
        self.received_count += 1
        received = received_at_utc or _utc_now()
        source_digest = keyed_digest(
            self.rotation_secret, "remote-id-live-input", payload
        )
        boot_id = payload.get("sensor_boot_id")
        sequence = payload.get("source_sequence")
        if sequence is not None:
            if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
                raise ValueError("Remote ID source_sequence must be a nonnegative integer")
            key = (str(boot_id or "UNSPECIFIED_BOOT"), sequence)
            prior = self.seen_sequences.get(key)
            if prior is not None:
                if prior != source_digest:
                    raise ValueError("Remote ID source sequence was reused with different content")
                self.duplicate_count += 1
                return [{"kind": "duplicate_remote_id_input", "source_sequence": sequence}]
            self.seen_sequences[key] = source_digest

        normalized_payload = dict(payload)
        observed = str(payload.get("observed_at_utc") or received)
        source_time_state = "HOST_RECEIPT_ONLY"
        if payload.get("observed_at_utc") is not None:
            source_time_state = "SOURCE_TIMESTAMPED"
            skew = abs((_instant(received) - _instant(observed)).total_seconds())
            if skew > self.max_source_clock_skew_seconds:
                source_time_state = "CLOCK_CONTRADICTED"
                normalized_payload["validity"] = "CONTRADICTED"

        pose = self.latest_pose
        pose_ref = None
        if pose is not None:
            age = abs((_instant(observed) - _instant(pose["observed_at_utc"])).total_seconds())
            if age <= self.max_pose_age_seconds:
                pose_ref = pose["pose_id"]

        lineage = self._persist_lineage()
        observation = normalize(
            normalized_payload,
            observed_at_utc=observed,
            ingested_at_utc=received,
            receiver_id=self.receiver_id,
            hardware_profile_id=self.hardware_profile_id,
            rotation_epoch=self.rotation_epoch,
            rotation_secret=self.rotation_secret,
            pose_ref=pose_ref,
            clock_uncertainty_ms=float(payload.get("clock_uncertainty_ms", 1000.0)),
            host_monotonic_ns=host_monotonic_ns,
            sensor_boot_id=None if boot_id is None else str(boot_id),
            source_sequence=sequence,
            clock_epoch_id=str(payload.get("clock_epoch_id", "rid-host-clock-epoch-0")),
            source_time_state=source_time_state,
            measurement_lineage_id=self._lineage_id,
            upstream_receiver_revision=self.upstream_receiver_revision,
        )
        message = make_remote_id_message(
            normalized_payload, observation,
            receiver_revision=self.upstream_receiver_revision,
            core_revision=self.upstream_core_revision,
        )
        message_receipt = make_receipt(
            subject_ref=message["message_id"],
            input_refs=[observation["observation_id"]],
            input_hashes=[sha256_uri(observation)],
            algorithm_name="decoded_remote_id_message_typer",
            algorithm_version="0.3.0",
            parameters={
                "raw_identifier_retention": "ROTATING_HASH",
                "operator_or_takeoff_position": "EXCLUDED_FROM_ORDINARY_LEDGER",
                "authentication_claim_ceiling": "NOT_CHECKED",
            },
            output=message,
            source_locks=_source_locks(
                self.upstream_receiver_revision, self.upstream_core_revision
            ),
            code_revision=CODE_REVISION,
            code_digest=runtime_source_digest(),
        )
        if self.ledger is not None:
            self.ledger.append_event("observation", observation["observation_id"], observation)
            self.ledger.append_event("evidence_receipt", message_receipt["receipt_id"], message_receipt)
            self.ledger.append_event("remote_id_message", message["message_id"], message)
        self.accepted_count += 1
        generated: list[dict[str, Any]] = [
            {"kind": "observation", "value": observation},
            {"kind": "remote_id_message", "value": message},
            {"kind": "evidence_receipt", "value": message_receipt},
        ]

        association = None
        association_receipt = None
        if pose_ref is not None and pose is not None:
            association, association_receipt = _association(
                observation, pose,
                max_pose_offset_ms=(self.max_pose_age_seconds * 1000.0
                                    + float(observation["clock_uncertainty_ms"])
                                    + float(pose["clock_uncertainty_ms"])),
                rotation_secret=self.rotation_secret,
                code_digest=runtime_source_digest(),
            )
            if self.ledger is not None:
                self.ledger.append_event(
                    "pose_association", association["association_id"], association
                )
                self.ledger.append_event(
                    "evidence_receipt", association_receipt["receipt_id"], association_receipt
                )
            generated.extend([
                {"kind": "pose_association", "value": association},
                {"kind": "evidence_receipt", "value": association_receipt},
            ])

        remote = observation["measurement"]["remote_id"]
        emitter_key = observation["emitter"]["ephemeral_emitter_key"]
        position = remote["aircraft_position"]
        if emitter_key is None or position is None or remote["validity"] in {"MALFORMED", "CONTRADICTED"}:
            generated.append({
                "kind": "remote_id_evidence_state",
                "observation_ref": observation["observation_id"],
                "validity": remote["validity"],
                "track_updated": False,
                "surveillance_capability_claim": False,
            })
            if remote["validity"] == "CONTRADICTED" and emitter_key in self.groups:
                previous_ref = self.groups[emitter_key]["observations"][-1]["observation_id"]
                contradiction = self._contradiction(
                    emitter_key, previous_ref, observation["observation_id"], observed
                )
                if self.ledger is not None:
                    self.ledger.append_event(
                        "contradiction", contradiction["contradiction_id"], contradiction
                    )
                self.groups[emitter_key]["contradictions"].append(contradiction)
                generated.append({"kind": "contradiction", "value": contradiction})
                generated.extend(self._append_track_revision(
                    self.groups[emitter_key], observation, message, message_receipt,
                    lineage, association, association_receipt,
                ))
            return generated

        group = self.groups.setdefault(emitter_key, {
            "track_id": keyed_content_id(
                "track", self.rotation_secret,
                {"lineage": self._lineage_id, "emitter_key": emitter_key,
                 "basis": "BROADCAST_REMOTE_ID"}, 40,
            ),
            "points": [], "observations": [], "messages": [], "contradictions": [],
            "last_track_revision": None, "last_track_hash": None,
        })
        if group["points"] and _instant(observed) <= _instant(group["points"][-1]["observed_at_utc"]):
            contradiction = self._contradiction(
                emitter_key, group["observations"][-1]["observation_id"],
                observation["observation_id"], observed,
            )
            if self.ledger is not None:
                self.ledger.append_event(
                    "contradiction", contradiction["contradiction_id"], contradiction
                )
            group["contradictions"].append(contradiction)
            generated.extend([
                {"kind": "contradiction", "value": contradiction},
                {"kind": "remote_id_evidence_state", "validity": "CONTRADICTED",
                 "observation_ref": observation["observation_id"], "track_updated": False,
                 "surveillance_capability_claim": False},
            ])
            generated.extend(self._append_track_revision(
                group, observation, message, message_receipt, lineage,
                association, association_receipt,
            ))
            return generated

        point = {
            "observation_ref": observation["observation_id"],
            "observed_at_utc": observed,
            "latitude": position["latitude"],
            "longitude": position["longitude"],
            "altitude_m": position["altitude_m"],
            "horizontal_accuracy_m": position["horizontal_accuracy_m"],
            "speed_mps": remote["speed_mps"],
            "heading_deg": remote["heading_deg"],
            "validity": remote["validity"],
            "basis": "BROADCAST_REMOTE_ID",
        }
        group["points"].append(point)
        group["observations"].append(observation)
        group["messages"].append(message)
        generated.extend(self._append_track_revision(
            group, observation, message, message_receipt, lineage,
            association, association_receipt,
        ))
        return generated

    def _contradiction(
        self, emitter_key: str, prior_ref: str, current_ref: str, created_at_utc: str,
    ) -> dict[str, Any]:
        core = {
            "schema_version": "1.0.0",
            "subject_ref": emitter_key,
            "assertion_a_refs": [prior_ref],
            "assertion_b_refs": [current_ref],
            "kind": "REMOTE_ID_VALIDITY",
            "state": "OPEN",
            "explanation": (
                "Decoded Remote ID timing or validity contradicts the prior track; "
                "the observations remain separate and were not silently fused."
            ),
            "resolution_refs": [],
            "created_at_utc": created_at_utc,
        }
        event = {**core, "contradiction_id": content_id("conflict", core, 40)}
        event["content_hash"] = sha256_uri(event)
        return event

    def _append_track_revision(
        self, group: dict[str, Any], observation: dict[str, Any], message: dict[str, Any],
        message_receipt: dict[str, Any], lineage: dict[str, Any],
        association: dict[str, Any] | None, association_receipt: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        engine = MobileTrack(group["track_id"], "BROADCAST_REMOTE_ID")
        for point in group["points"]:
            engine.add(TrackPoint(
                observed_at_utc=point["observed_at_utc"],
                latitude=point["latitude"], longitude=point["longitude"],
                horizontal_accuracy_m=point["horizontal_accuracy_m"],
                evidence_basis="BROADCAST_REMOTE_ID",
            ))
        motion_state = engine.state()
        if group["contradictions"]:
            motion_state = "MIXED_OR_CONTRADICTED"
        revision = 1 if group["last_track_revision"] is None else int(
            group["last_track_revision"]["revision"]
        ) + 1
        track_core = {
            "schema_version": "1.0.0",
            "track_id": group["track_id"],
            "revision": revision,
            "parent_revision_hash": group["last_track_hash"],
            "evidence_basis": "BROADCAST_REMOTE_ID",
            "motion_state": motion_state,
            "points": list(group["points"]),
            "observer_pose_association_refs": [] if association is None
                else [association["association_id"]],
            "contradiction_refs": [
                item["contradiction_id"] for item in group["contradictions"]
            ],
            "calibration_state": "UNCALIBRATED",
            "confidence_level": None,
        }
        track_revision_id = content_id("trackrev", track_core, 40)
        track_output = {**track_core, "track_revision_id": track_revision_id}
        inputs = [observation, message, message_receipt]
        if association is not None and association_receipt is not None:
            inputs.extend([association, association_receipt])
        input_refs = [
            observation["observation_id"], message["message_id"],
            message_receipt["receipt_id"],
        ]
        input_hashes = [sha256_uri(item) for item in inputs[:3]]
        if association is not None and association_receipt is not None:
            input_refs.extend([association["association_id"], association_receipt["receipt_id"]])
            input_hashes.extend([sha256_uri(association), sha256_uri(association_receipt)])
        if group["last_track_revision"] is not None:
            input_refs.append(group["last_track_revision"]["track_revision_id"])
            input_hashes.append(group["last_track_hash"])
        track_receipt = make_receipt(
            subject_ref=track_revision_id,
            input_refs=input_refs,
            input_hashes=input_hashes,
            algorithm_name="broadcast_remote_id_track_assembler",
            algorithm_version="0.3.0",
            parameters={
                "evidence_basis": "BROADCAST_REMOTE_ID",
                "observer_pose_basis": "SEPARATE_RESTRICTED_ASSOCIATION",
                "mobility_rule": "endpoint-displacement-greater-than-max-30m-or-2x-mean-accuracy",
                "calibration_state": "UNCALIBRATED",
                "remote_id_is_surveillance_authority": False,
            },
            output=track_output,
            source_locks=_source_locks(
                self.upstream_receiver_revision, self.upstream_core_revision
            ),
            code_revision=CODE_REVISION,
            code_digest=runtime_source_digest(),
        )
        track_revision = {**track_output, "receipt_id": track_receipt["receipt_id"]}
        if self.ledger is not None:
            self.ledger.append_event(
                "evidence_receipt", track_receipt["receipt_id"], track_receipt
            )
            track_hash = self.ledger.append_event(
                "mobile_track_revision", track_revision_id, track_revision
            )
        else:
            track_hash = sha256_uri(track_revision)
        group["last_track_revision"] = track_revision
        group["last_track_hash"] = track_hash
        generated = [
            {"kind": "mobile_track_revision", "value": track_revision},
            {"kind": "evidence_receipt", "value": track_receipt},
        ]
        if motion_state == "MOBILE":
            generated.extend(self._append_node_and_alert(
                group, observation, message, message_receipt, lineage,
                track_revision, track_receipt, association, association_receipt,
            ))
        return generated

    def _append_node_and_alert(
        self, group: dict[str, Any], observation: dict[str, Any], message: dict[str, Any],
        message_receipt: dict[str, Any], lineage: dict[str, Any],
        track_revision: dict[str, Any], track_receipt: dict[str, Any],
        association: dict[str, Any] | None, association_receipt: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        node_id = keyed_content_id(
            "node", self.rotation_secret,
            {"track_id": group["track_id"], "basis": "BROADCAST_REMOTE_ID"}, 40,
        )
        previous = self.node_state.get(group["track_id"])
        revision = 1 if previous is None else int(previous["revision"]) + 1
        evidence_items = [observation, message, message_receipt, track_revision, track_receipt]
        evidence_refs = [
            observation["observation_id"], message["message_id"],
            message_receipt["receipt_id"], track_revision["track_revision_id"],
            track_receipt["receipt_id"],
        ]
        if association is not None and association_receipt is not None:
            evidence_items.extend([association, association_receipt])
            evidence_refs.extend([association["association_id"], association_receipt["receipt_id"]])
        contradiction_refs = [
            item["contradiction_id"] for item in group["contradictions"]
        ]
        node_body = {
            "schema_version": "1.0.0",
            "node_id": node_id,
            "revision": revision,
            "parent_revision_hash": None if previous is None else previous["ledger_hash"],
            "motion_state": "MOBILE",
            "asset_kind_hypotheses": ["DRONE"],
            "evidence_state": "CONTRADICTED" if contradiction_refs else "MEASURED",
            "lifecycle_state": "CANDIDATE",
            "claim_level": "MOBILE_TRACK",
            "classification": {
                "ranked_labels": [
                    "REMOTE_ID_AIRCRAFT_BROADCAST",
                    "SURVEILLANCE_CAPABILITY_UNDETERMINED",
                ],
                "probabilities": None,
                "calibration_state": "UNCALIBRATED",
                "confidence_label": "UNKNOWN",
            },
            "location": None,
            "trajectory": list(group["points"]),
            "evidence_refs": sorted(evidence_refs),
            "independent_source_lineages": [],
            "measurement_lineages": [self._lineage_id],
            "contradiction_refs": sorted(contradiction_refs),
            "updated_at_utc": observation["observed_at_utc"],
            "publication_state": "PRIVATE_LOCAL",
        }
        evidence_hashes = {
            ref: sha256_uri(item) for ref, item in zip(evidence_refs, evidence_items, strict=True)
        }
        input_refs = list(node_body["evidence_refs"]) + [self._lineage_id] + contradiction_refs
        input_hashes = [evidence_hashes[ref] for ref in node_body["evidence_refs"]]
        input_hashes.append(sha256_uri(lineage))
        contradiction_hashes = {
            item["contradiction_id"]: sha256_uri(item) for item in group["contradictions"]
        }
        input_hashes.extend(contradiction_hashes[ref] for ref in contradiction_refs)
        if previous is not None:
            input_refs.append(f"{node_id}:revision:{revision - 1}")
            input_hashes.append(previous["ledger_hash"])
        node_receipt = make_receipt(
            subject_ref=f"{node_id}:revision:{revision}",
            input_refs=input_refs,
            input_hashes=input_hashes,
            algorithm_name="node_revision_assembler",
            algorithm_version="0.3.0",
            parameters={
                "claim_ceiling": "REMOTE_ID_MOBILE_TRACK",
                "surveillance_capability_claim": False,
                "location_basis": "BROADCAST_REMOTE_ID_ONLY",
                "observer_motion_fused_into_emitter_track": False,
                "calibration_required_for_probability": True,
            },
            output=node_body,
            source_locks=_source_locks(
                self.upstream_receiver_revision, self.upstream_core_revision
            ),
            code_revision=CODE_REVISION,
            code_digest=runtime_source_digest(),
        )
        node = {**node_body, "receipt_id": node_receipt["receipt_id"]}
        if self.ledger is not None:
            self.ledger.append_event(
                "evidence_receipt", node_receipt["receipt_id"], node_receipt
            )
            ledger_hash = self.ledger.append_node_revision(node)
        else:
            ledger_hash = sha256_uri(node)
        self.node_state[group["track_id"]] = {
            "revision": revision, "ledger_hash": ledger_hash,
        }

        alert_core = {
            "schema_version": "1.0.0",
            "alert_type": "REMOTE_ID_MOBILE_TRACK_OBSERVED",
            "created_at_utc": observation["observed_at_utc"],
            "observation_ref": observation["observation_id"],
            "track_revision_ref": track_revision["track_revision_id"],
            "node_revision_ref": f"{node_id}:revision:{revision}",
            "evidence_basis": "BROADCAST_REMOTE_ID",
            "motion_state": "MOBILE",
            "remote_id_validity": observation["measurement"]["remote_id"]["validity"],
            "surveillance_capability_claim": False,
            "probability": None,
            "publication_state": "PRIVATE_LOCAL",
        }
        alert_id = content_id("alert", alert_core, 40)
        alert_output = {**alert_core, "local_alert_id": alert_id}
        alert_receipt = make_receipt(
            subject_ref=alert_id,
            input_refs=[
                observation["observation_id"], track_revision["track_revision_id"],
                f"{node_id}:revision:{revision}",
            ],
            input_hashes=[sha256_uri(observation), sha256_uri(track_revision), ledger_hash],
            algorithm_name="private_local_mobile_alert",
            algorithm_version="0.3.0",
            parameters={
                "required_motion_state": "MOBILE",
                "public_delivery": False,
                "surveillance_capability_claim": False,
            },
            output=alert_output,
            source_locks=[],
            code_revision=CODE_REVISION,
            code_digest=runtime_source_digest(),
        )
        alert = {**alert_output, "receipt_id": alert_receipt["receipt_id"]}
        if self.ledger is not None:
            self.ledger.append_event(
                "evidence_receipt", alert_receipt["receipt_id"], alert_receipt
            )
            self.ledger.append_event("local_alert", alert_id, alert)
        return [
            {"kind": "node_revision", "value": node},
            {"kind": "evidence_receipt", "value": node_receipt},
            {"kind": "local_alert", "value": alert},
            {"kind": "evidence_receipt", "value": alert_receipt},
        ]

    def flush(self, observed_at_utc: str | None = None) -> list[dict[str, Any]]:
        return self.ingest_status(
            {"event": "receiver_status", "state": "STOPPED",
             "reason_codes": ["SESSION_FLUSH"]},
            received_at_utc=observed_at_utc,
        )
