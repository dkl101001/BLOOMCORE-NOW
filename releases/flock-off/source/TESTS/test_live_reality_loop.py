from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flockoff.crypto import FieldCipher
from flockoff.ledger import EvidenceLedger
from flockoff.live import LiveRealityLoop, TargetExpectation, strict_json_object
from flockoff.schema_guard import validate

SECRET = bytes(range(32))
ROUTE_KEY = bytes(reversed(range(32)))


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class LiveRealityLoopTests(unittest.TestCase):
    def setUp(self):
        self.signature = read_json(ROOT / "SIGNATURES" / "candidate" / "flock_you_wifi_assertion_v0.1.0.json")
        self.target = TargetExpectation.from_dict({
            "schema_version": "1.2.0",
            "target_asset_ref": "asset:known-condor-like-target",
            "signature_ref": "FLOCK_YOU_WIFI_ASSERTION@0.1.0",
            "latitude": 36.0,
            "longitude": -86.0,
            "trigger_radius_m": 90,
            "exit_radius_m": 130,
            "target_evidence_refs": ["public:fixture-target-record"],
            "failed_assumption": "the current 2.4 GHz detector aperture is sufficient for this target",
            "next_tests": [
                "establish scan-completeness telemetry for the current receiver",
                "characterize additional passive emission surfaces",
            ],
            "minimum_pose_count": 2,
            "cooldown_seconds": 0,
        })

    def pose(self, timestamp: str, lat: float, lon: float):
        return {
            "receiver_id": "rx-live",
            "observed_at_utc": timestamp,
            "latitude": lat,
            "longitude": lon,
            "horizontal_accuracy_m": 4.0,
            "clock_uncertainty_ms": 20.0,
            "source": "GNSS",
        }

    def payload(self, rssi=-52):
        return {
            "event": "detection",
            "detection_method": "wifi_wildcard_probe_ie_sig",
            "detection_tier": 4,
            "protocol": "wifi_2_4ghz",
            "mac_address": "82:6b:f2:14:07:3a",
            "oui": "82:6b:f2",
            "device_name": "",
            "rssi": rssi,
            "channel": 6,
            "frequency": 2437,
            "ssid": "",
        }

    def make_loop(self, ledger=None):
        return LiveRealityLoop(
            signature=self.signature,
            expectations=[self.target],
            receiver_id="rx-live",
            hardware_profile_id="xiao-esp32s3-flock-you-2g4",
            rotation_epoch="test-live",
            rotation_secret=SECRET,
            ledger=ledger,
            max_pose_age_seconds=3,
            upstream_build_ref="test-flashed-build",
            session_id="session-live-test",
        )

    def test_real_world_miss_recurses_automatically_without_absence_claim(self):
        loop = self.make_loop()
        loop.mark_sensor_connected("2026-08-23T16:00:00Z")
        self.assertEqual(loop.ingest_pose(self.pose("2026-08-23T16:00:00Z", 36.0, -86.0005)), [])
        self.assertEqual(loop.ingest_pose(self.pose("2026-08-23T16:00:01Z", 36.0, -86.0002)), [])
        generated = loop.ingest_pose(self.pose("2026-08-23T16:00:02Z", 36.0, -86.0020))
        kinds = [item["kind"] for item in generated]
        self.assertEqual(kinds, ["sensor_coverage", "failure_packet", "discovery_campaign"])
        coverage = generated[0]["value"]
        failure = generated[1]["value"]
        campaign = generated[2]["value"]
        self.assertEqual(coverage["state"], "PARTIAL")
        self.assertFalse(failure["absence_claim_permitted"])
        self.assertEqual(failure["observation_refs"], [])
        self.assertIn("public:fixture-target-record", failure["context_refs"])
        self.assertEqual(campaign["state"], "SENSING_APERTURE_INSUFFICIENT")
        self.assertTrue(campaign["next_tests"])
        validate(failure, read_json(ROOT / "SCHEMAS" / "failure_packet.schema.json"))
        validate(campaign, read_json(ROOT / "SCHEMAS" / "discovery_campaign.schema.json"))
        validate(coverage, read_json(ROOT / "SCHEMAS" / "sensor_coverage.schema.json"))

    def test_compatible_live_detection_suppresses_miss_but_does_not_prove_target_identity(self):
        loop = self.make_loop()
        loop.ingest_pose(self.pose("2026-08-23T16:00:00Z", 36.0, -86.0005))
        loop.ingest_pose(self.pose("2026-08-23T16:00:01Z", 36.0, -86.0002))
        events = loop.ingest_flock_you(
            self.payload(), received_at_utc="2026-08-23T16:00:01Z", host_monotonic_ns=1
        )
        self.assertEqual(events[1]["value"]["match_state"], "MATCH")
        generated = loop.ingest_pose(self.pose("2026-08-23T16:00:02Z", 36.0, -86.0020))
        self.assertEqual(len(generated), 1)
        self.assertEqual(generated[0]["kind"], "target_window_match")
        self.assertFalse(generated[0]["target_identity_proven"])
        self.assertEqual(generated[0]["claim"], "COMPATIBLE_SIGNATURE_OBSERVED_IN_TARGET_WINDOW")

    def test_live_failure_and_campaign_revisions_are_in_immutable_ledger(self):
        with tempfile.TemporaryDirectory() as temporary:
            db = Path(temporary) / "live.sqlite"
            migration = ROOT / "SCHEMAS" / "migrations" / "0001_initial.sql"
            with EvidenceLedger(
                db, migration, FieldCipher(ROUTE_KEY), evidence_digest_secret=SECRET,
            ) as ledger:
                loop = self.make_loop(ledger)
                loop.mark_sensor_connected("2026-08-23T16:00:00Z")
                loop.ingest_pose(self.pose("2026-08-23T16:00:00Z", 36.0, -86.0005))
                loop.ingest_pose(self.pose("2026-08-23T16:00:01Z", 36.0, -86.0002))
                generated = loop.ingest_pose(self.pose("2026-08-23T16:00:02Z", 36.0, -86.0020))
                failure = generated[1]["value"]
                campaign = generated[2]["value"]
                stored_failure = ledger.get_event("failure_packet", failure["failure_id"])
                self.assertEqual(stored_failure, failure)
                first = ledger.get_discovery_campaign_revision(campaign["campaign_id"], 1)
                second = ledger.get_discovery_campaign_revision(campaign["campaign_id"], 2)
                self.assertEqual(first["state"], "HUNTING")
                self.assertEqual(second["state"], "SENSING_APERTURE_INSUFFICIENT")
                self.assertEqual(second["parent_campaign_hash"], first["content_hash"])
                applied = {
                    row[0] for row in ledger.connection.execute("SELECT migration_id FROM schema_migrations")
                }
                self.assertIn("0002_recursive_live_campaign_revisions", applied)



    def test_nonmatching_live_observation_is_preserved_inside_failure_packet(self):
        loop = self.make_loop()
        loop.ingest_pose(self.pose("2026-08-23T16:10:00Z", 36.0, -86.0005))
        loop.ingest_pose(self.pose("2026-08-23T16:10:01Z", 36.0, -86.0002))
        payload = self.payload()
        payload["detection_method"] = "wifi_wildcard_probe"
        payload["detection_tier"] = 3
        events = loop.ingest_flock_you(
            payload, received_at_utc="2026-08-23T16:10:01Z", host_monotonic_ns=2
        )
        self.assertEqual(events[1]["value"]["match_state"], "NO_MATCH")
        generated = loop.ingest_pose(self.pose("2026-08-23T16:10:02Z", 36.0, -86.0020))
        failure = next(item["value"] for item in generated if item["kind"] == "failure_packet")
        self.assertEqual(failure["observation_refs"], [events[0]["value"]["observation_id"]])

    def test_two_explicit_live_passes_build_private_node_and_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            db = Path(temporary) / "nodes.sqlite"
            migration = ROOT / "SCHEMAS" / "migrations" / "0001_initial.sql"
            with EvidenceLedger(
                db, migration, FieldCipher(ROUTE_KEY), evidence_digest_secret=SECRET,
            ) as ledger:
                loop = LiveRealityLoop(
                    signature=self.signature, expectations=[], receiver_id="rx-live",
                    hardware_profile_id="xiao-esp32s3-flock-you-2g4",
                    rotation_epoch="node-live", rotation_secret=SECRET, ledger=ledger,
                    upstream_build_ref="test-flashed-build", session_id="node-session",
                )
                samples = [
                    ("p1", "2026-08-23T17:00:00Z", 36.0003, -86.0010, -67),
                    ("p1", "2026-08-23T17:00:01Z", 36.0003, -86.0003, -51),
                    ("p1", "2026-08-23T17:00:02Z", 36.0003, -85.9997, -51),
                    ("p1", "2026-08-23T17:00:03Z", 36.0003, -85.9990, -67),
                    ("p2", "2026-08-23T17:01:00Z", 35.9990, -86.0003, -67),
                    ("p2", "2026-08-23T17:01:01Z", 35.9997, -86.0003, -51),
                    ("p2", "2026-08-23T17:01:02Z", 36.0003, -86.0003, -51),
                    ("p2", "2026-08-23T17:01:03Z", 36.0010, -86.0003, -67),
                ]
                node_events = []
                for pass_id, timestamp, lat, lon, rssi in samples:
                    pose = self.pose(timestamp, lat, lon)
                    pose["pass_id"] = pass_id
                    loop.ingest_pose(pose)
                    events = loop.ingest_flock_you(
                        self.payload(rssi), received_at_utc=timestamp, host_monotonic_ns=1
                    )
                    node_events.extend(item for item in events if item["kind"] == "node_revision")
                self.assertTrue(node_events)
                node = node_events[-1]["value"]
                self.assertEqual(node["publication_state"], "PRIVATE_LOCAL")
                self.assertEqual(node["classification"]["calibration_state"], "UNCALIBRATED")
                self.assertIsNone(node["classification"]["probabilities"])
                row = ledger.connection.execute(
                    "SELECT COUNT(*) FROM node_revisions WHERE node_id=?", (node["node_id"],)
                ).fetchone()
                self.assertGreaterEqual(row[0], 1)
                receipt = ledger.get_event("evidence_receipt", node["receipt_id"])
                self.assertEqual(receipt["body"]["subject_ref"], f"{node['node_id']}:revision:{node['revision']}")

    def test_live_build_provenance_is_operator_supplied_not_falsely_pinned(self):
        loop = self.make_loop()
        loop.ingest_pose(self.pose("2026-08-23T16:00:00Z", 36.0, -86.0005))
        events = loop.ingest_flock_you(
            self.payload(), received_at_utc="2026-08-23T16:00:00Z", host_monotonic_ns=1
        )
        observation = events[0]["value"]
        self.assertEqual(observation["provenance"]["adapter_commit_or_version"], "test-flashed-build")

    def test_strict_live_json_rejects_duplicate_keys_and_nonfinite(self):
        with self.assertRaises(ValueError):
            strict_json_object('{"event":"config","event":"detection"}')
        with self.assertRaises(ValueError):
            strict_json_object('{"x":NaN}')

    def test_target_exit_radius_hysteresis_is_required(self):
        with self.assertRaises(ValueError):
            TargetExpectation.from_dict({
                "target_asset_ref": "asset:x", "signature_ref": "FLOCK_YOU_WIFI_ASSERTION@0.1.0",
                "latitude": 0, "longitude": 0, "trigger_radius_m": 100, "exit_radius_m": 50,
                "target_evidence_refs": ["source:x"], "failed_assumption": "test",
                "next_tests": ["test next"]
            })


if __name__ == "__main__":
    unittest.main()
