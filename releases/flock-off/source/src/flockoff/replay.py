"""Deterministic host-side replay for normalized evidence and receipts."""

from __future__ import annotations

import datetime as dt
from typing import Any

from . import CODE_REVISION, runtime_source_digest
from .adapters.flock_you import ADAPTER_VERSION, UPSTREAM_COMMIT, UPSTREAM_URL, normalize
from .canonical import content_id, keyed_content_id, keyed_digest, sha256_uri
from .inference import Sample, localize_static
from .receipts import make_receipt
from .signatures import evaluate, signature_content_hash


def make_pose(record: dict[str, Any], *, id_secret: bytes) -> dict[str, Any]:
    core = {
        "schema_version": "1.0.0",
        "receiver_id": record["receiver_id"],
        "observed_at_utc": record["observed_at_utc"],
        "clock_uncertainty_ms": float(record.get("clock_uncertainty_ms", 10.0)),
        "position": {
            "latitude": float(record["latitude"]),
            "longitude": float(record["longitude"]),
            "altitude_m": record.get("altitude_m"),
            "horizontal_accuracy_m": float(record.get("horizontal_accuracy_m", 5.0)),
            "vertical_accuracy_m": record.get("vertical_accuracy_m"),
            "source": record.get("source", "SYNTHETIC"),
        },
        "heading_deg": record.get("heading_deg"),
        "speed_mps": record.get("speed_mps"),
        "privacy": {"class": "RESTRICTED_ROUTE", "public_export_allowed": False},
        "provenance": {
            "source": record.get("source_ref", "replay-fixture"),
            "content_hash": sha256_uri(record),
        },
    }
    core["pose_id"] = keyed_content_id("pose", id_secret, core, 40)
    return core


def _instant(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a UTC offset")
    return parsed.astimezone(dt.UTC)


def _make_pass_partition(
    observation_pass_map: dict[str, str], *, session_id: str, code_digest: str
) -> dict[str, Any]:
    core = {
        "schema_version": "1.0.0",
        "session_id": session_id,
        "algorithm": {
            "name": "caller_explicit_pass_partition",
            "version": "1.0.0",
            "code_revision": CODE_REVISION,
            "code_digest": code_digest,
        },
        "observation_pass_map": dict(sorted(observation_pass_map.items())),
    }
    partition = {**core, "partition_id": content_id("partition", core, 40)}
    partition["content_hash"] = sha256_uri(partition)
    return partition


def _association(
    observation: dict[str, Any], pose: dict[str, Any], *, max_pose_offset_ms: float,
    rotation_secret: bytes, code_digest: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if observation["receiver"]["receiver_id"] != pose["receiver_id"]:
        raise ValueError("observation and pose receiver IDs differ")
    offset_ms = (
        _instant(observation["observed_at_utc"]) - _instant(pose["observed_at_utc"])
    ).total_seconds() * 1000.0
    if abs(offset_ms) > max_pose_offset_ms:
        raise ValueError(
            f"nearest pose is {abs(offset_ms):.1f} ms away; limit is {max_pose_offset_ms:.1f} ms"
        )
    core = {
        "schema_version": "1.0.0",
        "observation_ref": observation["observation_id"],
        "pose_refs": [pose["pose_id"]],
        "method": "EXACT_TIMESTAMP" if offset_ms == 0 else "NEAREST_NEIGHBOR",
        "time_offset_ms": offset_ms,
        "association_uncertainty_ms": (
            abs(offset_ms)
            + float(observation["clock_uncertainty_ms"])
            + float(pose["clock_uncertainty_ms"])
        ),
    }
    association_id = content_id("assoc", core, 40)
    output = {**core, "association_id": association_id}
    receipt = make_receipt(
        subject_ref=association_id,
        input_refs=[observation["observation_id"], pose["pose_id"]],
        input_hashes=[
            sha256_uri(observation),
            keyed_digest(rotation_secret, "restricted-pose-receipt", pose),
        ],
        algorithm_name="observation_pose_association",
        algorithm_version="1.0.0",
        parameters={
            "maximum_pose_offset_ms": max_pose_offset_ms,
            "receiver_id_equality_required": True,
            "method": core["method"],
        },
        output=output,
        source_locks=[],
        code_revision=CODE_REVISION,
        code_digest=code_digest,
    )
    return {**output, "receipt_id": receipt["receipt_id"]}, receipt


def _item_ref(item: dict[str, Any]) -> str:
    for name in (
        "observation_id", "match_id", "association_id", "partition_id",
        "measurement_lineage_id", "message_id", "track_revision_id",
        "local_alert_id", "receipt_id",
    ):
        if name in item:
            return str(item[name])
    raise ValueError("receipt input has no stable reference")


def run_records(
    records: list[dict[str, Any]], *, signature: dict[str, Any],
    rotation_secret: bytes, rotation_epoch: str = "replay-session-1",
    include_restricted: bool = False,
) -> dict[str, Any]:
    """Replay records without networking.

    Restricted receiver poses are omitted from the returned value by default.
    A trusted storage caller may request them solely to place them into the
    encrypted route vault before discarding the plaintext in memory.
    """

    poses: dict[str, dict[str, Any]] = {}
    try:
        expected_signature_hash = signature_content_hash(signature)
    except KeyError as exc:
        raise ValueError("signature is missing provenance custody") from exc
    if signature.get("provenance", {}).get("content_hash") != expected_signature_hash:
        raise ValueError("signature content hash mismatch")
    used_pose_ids: set[str] = set()
    observations: list[dict[str, Any]] = []
    matches: list[dict[str, Any]] = []
    pose_associations: list[dict[str, Any]] = []
    association_receipts: list[dict[str, Any]] = []
    lineage_meta: dict[str, dict[str, Any]] = {}
    groups: dict[str, dict[str, Any]] = {}
    code_digest = runtime_source_digest()

    for index, record in enumerate(records):
        kind = record.get("kind")
        if kind == "pose":
            pose = make_pose(record, id_secret=rotation_secret)
            alias = str(record.get("alias", pose["pose_id"]))
            if alias in poses:
                raise ValueError(f"record {index}: duplicate pose alias {alias!r}")
            poses[alias] = pose
            continue
        if kind != "flock_you_detection":
            raise ValueError(f"record {index}: unsupported replay kind {kind!r}")
        alias = str(record["pose_alias"])
        if alias not in poses:
            raise ValueError(f"record {index}: unknown pose alias {alias!r}")
        pose = poses[alias]
        if record.get("receiver_id", pose["receiver_id"]) != pose["receiver_id"]:
            raise ValueError(f"record {index}: record and pose receiver IDs differ")
        pass_id = str(record.get("pass_id", "pass-1"))
        if not pass_id:
            raise ValueError(f"record {index}: pass ID cannot be empty")
        lineage_seed = {
            "session_id": rotation_epoch,
            "pass_id": pass_id,
            "receiver_id": pose["receiver_id"],
            "adapter": "flock_you_json",
        }
        lineage_id = keyed_content_id(
            "mlineage", rotation_secret, lineage_seed, 40
        )
        observation = normalize(
            record["payload"],
            observed_at_utc=record["observed_at_utc"],
            ingested_at_utc=record.get("ingested_at_utc", record["observed_at_utc"]),
            receiver_id=pose["receiver_id"],
            hardware_profile_id=record.get("hardware_profile_id", "xiao-esp32s3-flock-you-2g4"),
            rotation_epoch=rotation_epoch,
            rotation_secret=rotation_secret,
            pose_ref=pose["pose_id"],
            clock_uncertainty_ms=float(record.get("clock_uncertainty_ms", 1000.0)),
            host_monotonic_ns=record.get("host_monotonic_ns"),
            sensor_boot_id=record.get("sensor_boot_id", "fixture-boot-1"),
            source_sequence=record.get("source_sequence", index),
            measurement_lineage_id=lineage_id,
        )
        metadata = lineage_meta.setdefault(lineage_id, {
            **lineage_seed, "raw_input_digests": [],
        })
        metadata["raw_input_digests"].append(observation["provenance"]["raw_input_digest"])
        max_offset = float(record.get(
            "max_pose_offset_ms",
            float(pose["clock_uncertainty_ms"]) + float(observation["clock_uncertainty_ms"]),
        ))
        association, association_receipt = _association(
            observation, pose, max_pose_offset_ms=max_offset,
            rotation_secret=rotation_secret, code_digest=code_digest,
        )
        match = evaluate(observation, signature)
        emitter_key = observation["emitter"]["ephemeral_emitter_key"]
        if not emitter_key:
            raise ValueError("static replay requires a non-null ephemeral emitter key")
        group = groups.setdefault(emitter_key, {
            "observations": [], "matches": [], "samples": [], "associations": [],
            "association_receipts": [], "poses": {}, "pass_map": {},
        })
        group["observations"].append(observation)
        group["matches"].append(match)
        group["associations"].append(association)
        group["association_receipts"].append(association_receipt)
        group["poses"][pose["pose_id"]] = pose
        group["pass_map"][observation["observation_id"]] = pass_id
        group["samples"].append(Sample(
            latitude=pose["position"]["latitude"],
            longitude=pose["position"]["longitude"],
            rssi_dbm=float(observation["measurement"]["rssi_dbm"]),
            receiver_id=pose["receiver_id"],
            pass_id=pass_id,
            horizontal_accuracy_m=float(pose["position"]["horizontal_accuracy_m"]),
        ))
        used_pose_ids.add(pose["pose_id"])
        observations.append(observation)
        matches.append(match)
        pose_associations.append(association)
        association_receipts.append(association_receipt)

    if not observations:
        raise ValueError("replay contained no observations")

    measurement_lineages: dict[str, dict[str, Any]] = {}
    for lineage_id in sorted(lineage_meta):
        metadata = lineage_meta[lineage_id]
        core = {
            "schema_version": "1.0.0",
            "measurement_lineage_id": lineage_id,
            "raw_capture_digest": keyed_digest(
                rotation_secret, f"measurement-lineage:{lineage_id}",
                sorted(metadata["raw_input_digests"]),
            ),
            "session_id": metadata["session_id"],
            "pass_id": metadata["pass_id"],
            "receiver_id": metadata["receiver_id"],
            "calibration_profile_id": None,
            "normalization_transform": {
                "name": "flock_you_json_normalizer",
                "version": ADAPTER_VERSION,
                "code_revision": CODE_REVISION,
                "code_digest": code_digest,
            },
            "parent_lineage_ids": [],
        }
        measurement_lineages[lineage_id] = {
            **core, "content_hash": sha256_uri(core),
        }

    source_locks = [{
        "source_id": UPSTREAM_URL,
        "revision": UPSTREAM_COMMIT,
        "content_hash": None,
    }]
    node_revisions: list[dict[str, Any]] = []
    spatial_results: list[dict[str, Any]] = []
    spatial_receipts: list[dict[str, Any]] = []
    pass_partitions: list[dict[str, Any]] = []
    node_receipts: list[dict[str, Any]] = []

    for emitter_key in sorted(groups):
        group = groups[emitter_key]
        spatial = localize_static(group["samples"])
        group_lineages = [
            measurement_lineages[lineage_id] for lineage_id in sorted({
                item["measurement_lineage_id"] for item in group["observations"]
            })
        ]
        partition = _make_pass_partition(
            group["pass_map"], session_id=rotation_epoch, code_digest=code_digest
        )
        spatial_inputs = (
            group["observations"] + group["matches"] + list(group["poses"].values())
            + group["associations"] + group["association_receipts"]
            + group_lineages + [partition]
        )
        input_refs: list[str] = []
        input_hashes: list[str] = []
        for item in spatial_inputs:
            if "pose_id" in item:
                input_refs.append(item["pose_id"])
                input_hashes.append(keyed_digest(
                    rotation_secret, "restricted-pose-receipt", item
                ))
            else:
                input_refs.append(_item_ref(item))
                input_hashes.append(sha256_uri(item))
        spatial_receipt = make_receipt(
            subject_ref=f"static-rf-support-region:{emitter_key}",
            input_refs=input_refs,
            input_hashes=input_hashes,
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
            },
            output=spatial,
            source_locks=source_locks,
            code_revision=CODE_REVISION,
            code_digest=code_digest,
        )
        location = {key: value for key, value in spatial.items() if key != "diagnostics"}
        group_observations = group["observations"]
        group_matches = group["matches"]
        node_seed = {
            "measurement_lineages": sorted({
                item["measurement_lineage_id"] for item in group_observations
            }),
            "emitter_key": emitter_key,
        }
        latest_time = max(item["observed_at_utc"] for item in group_observations)
        matched = any(item["match_state"] == "MATCH" for item in group_matches)
        evidence_refs = sorted(
            [item["observation_id"] for item in group_observations]
            + [item["match_id"] for item in group_matches]
            + [item["association_id"] for item in group["associations"]]
            + [item["receipt_id"] for item in group["association_receipts"]]
            + [item["measurement_lineage_id"] for item in group_lineages]
            + [partition["partition_id"], spatial_receipt["receipt_id"]]
        )
        node_body = {
            "schema_version": "1.0.0",
            "node_id": content_id("node", node_seed, 32),
            "revision": 1,
            "parent_revision_hash": None,
            "motion_state": "MOTION_UNRESOLVED",
            "asset_kind_hypotheses": ["UNKNOWN"],
            "evidence_state": "MEASURED",
            "lifecycle_state": "CANDIDATE",
            "claim_level": "SIGNATURE_MATCH" if matched else "RF_ACTIVITY_PRESENT",
            "classification": {
                "ranked_labels": ["RF_PATTERN", "UNKNOWN"] if matched else ["UNKNOWN"],
                "probabilities": None,
                "calibration_state": "UNCALIBRATED",
                "confidence_label": "UNKNOWN",
            },
            "location": location,
            "trajectory": None,
            "evidence_refs": evidence_refs,
            "independent_source_lineages": [],
            "measurement_lineages": node_seed["measurement_lineages"],
            "contradiction_refs": [],
            "updated_at_utc": latest_time,
            "publication_state": "PRIVATE_LOCAL",
        }
        node_inputs = (
            group_observations + group_matches + group["associations"]
            + group["association_receipts"] + group_lineages + [partition, spatial_receipt]
        )
        node_receipt = make_receipt(
            subject_ref=f"{node_body['node_id']}:revision:1",
            input_refs=[_item_ref(item) for item in node_inputs],
            input_hashes=[sha256_uri(item) for item in node_inputs],
            algorithm_name="node_revision_assembler",
            algorithm_version="1.0.0",
            parameters={
                "claim_ceiling_policy": "candidate-rf-pattern-v1",
                "motion_default": "MOTION_UNRESOLVED",
                "calibration_required_for_probability": True,
                "emitter_partition": "ephemeral_emitter_key",
            },
            output=node_body,
            source_locks=source_locks,
            code_revision=CODE_REVISION,
            code_digest=code_digest,
        )
        node = {**node_body, "receipt_id": node_receipt["receipt_id"]}
        node_revisions.append(node)
        spatial_results.append(spatial)
        spatial_receipts.append(spatial_receipt)
        pass_partitions.append(partition)
        node_receipts.append(node_receipt)

    result: dict[str, Any] = {
        "pose_refs": sorted(used_pose_ids),
        "measurement_lineages": [measurement_lineages[key] for key in sorted(measurement_lineages)],
        "observations": observations,
        "signature_matches": matches,
        "pose_associations": pose_associations,
        "association_receipts": association_receipts,
        "pass_partitions": pass_partitions,
        "spatial_results": spatial_results,
        "spatial_receipts": spatial_receipts,
        "node_revisions": node_revisions,
        "receipts": association_receipts + spatial_receipts + node_receipts,
    }
    if include_restricted:
        result["poses"] = [
            pose for pose in poses.values() if pose["pose_id"] in used_pose_ids
        ]
    if len(node_revisions) == 1:
        result.update({
            "spatial_result": spatial_results[0],
            "spatial_receipt": spatial_receipts[0],
            "receipt": node_receipts[0],
            "node_revision": node_revisions[0],
        })
    return result
