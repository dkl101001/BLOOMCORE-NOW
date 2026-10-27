from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from flockoff.crypto import FieldCipher
from flockoff.ledger import EvidenceLedger
from flockoff.live_remote_id import RemoteIDLiveLoop
from flockoff.receipts import verify_receipt
from flockoff.schema_guard import validate


ROOT = Path(__file__).resolve().parents[1]
SECRET = bytes(range(32))


def rid(sequence: int, when: str, latitude: float, longitude: float, **updates):
    value = {
        "event": "remote_id",
        "message_type": "MESSAGE_PACK",
        "transport": "bluetooth_legacy",
        "validity": "VALID",
        "uas_id": "TEST-RID-0001",
        "uas_id_type": "SERIAL_NUMBER",
        "observed_at_utc": when,
        "clock_uncertainty_ms": 20,
        "sensor_boot_id": "receiver-boot-1",
        "source_sequence": sequence,
        "aircraft_position": {
            "latitude": latitude,
            "longitude": longitude,
            "altitude_m": 55.0,
            "horizontal_accuracy_m": 5.0,
        },
        "speed_mps": 12.0,
        "heading_deg": 45.0,
        "authentication_state": "NOT_PRESENT",
    }
    value.update(updates)
    return value


class LiveRemoteIDTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ledger = EvidenceLedger(
            self.root / "ledger.sqlite3",
            ROOT / "SCHEMAS" / "migrations" / "0001_initial.sql",
            FieldCipher(bytes(reversed(range(32)))),
            evidence_digest_secret=SECRET,
        )
        self.loop = RemoteIDLiveLoop(
            receiver_id="rid-rx-1",
            hardware_profile_id="opendroneid-external-decoded-v3.7.0",
            rotation_epoch="test-epoch",
            rotation_secret=SECRET,
            ledger=self.ledger,
            max_source_clock_skew_seconds=10.0,
            session_id="rid-test-session",
        )

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def pose(self, when: str, latitude: float, longitude: float):
        return self.loop.ingest_pose({
            "receiver_id": "rid-rx-1",
            "observed_at_utc": when,
            "latitude": latitude,
            "longitude": longitude,
            "horizontal_accuracy_m": 3.0,
            "source": "SYNTHETIC",
            "source_ref": "v0.3-test-pose",
        })

    def ingest(self, payload):
        return self.loop.ingest_remote_id(
            payload,
            received_at_utc=payload.get("observed_at_utc", "2026-08-23T12:00:00Z"),
            host_monotonic_ns=int(payload.get("source_sequence", 0)) + 100,
        )

    def test_complete_live_mobile_path_is_receipted_and_private(self):
        self.pose("2026-08-23T12:00:00Z", 34.0000, -84.0000)
        first = self.ingest(rid(1, "2026-08-23T12:00:01Z", 34.0010, -84.0010))
        self.pose("2026-08-23T12:00:01.500000Z", 34.0003, -84.0003)
        second = self.ingest(rid(2, "2026-08-23T12:00:02Z", 34.0020, -84.0020))

        self.assertIn("mobile_track_revision", [item["kind"] for item in first])
        self.assertEqual(
            [item["kind"] for item in second][-4:],
            ["node_revision", "evidence_receipt", "local_alert", "evidence_receipt"],
        )
        track = next(item["value"] for item in second if item["kind"] == "mobile_track_revision")
        node = next(item["value"] for item in second if item["kind"] == "node_revision")
        alert = next(item["value"] for item in second if item["kind"] == "local_alert")
        receipts = [item["value"] for item in second if item["kind"] == "evidence_receipt"]

        self.assertEqual(track["evidence_basis"], "BROADCAST_REMOTE_ID")
        self.assertEqual(track["motion_state"], "MOBILE")
        self.assertEqual(node["motion_state"], "MOBILE")
        self.assertEqual(node["asset_kind_hypotheses"], ["DRONE"])
        self.assertIn("SURVEILLANCE_CAPABILITY_UNDETERMINED", node["classification"]["ranked_labels"])
        self.assertIsNone(node["classification"]["probabilities"])
        self.assertIsNone(node["location"])
        self.assertFalse(alert["surveillance_capability_claim"])
        self.assertEqual(alert["publication_state"], "PRIVATE_LOCAL")
        self.assertTrue(all(verify_receipt(item) for item in receipts))
        self.assertNotIn("receiver_pose", json.dumps(track))
        self.assertNotIn("34.0003", json.dumps(track))

    def test_observer_and_emitter_motion_are_not_fused(self):
        self.pose("2026-08-23T12:00:00Z", 34.1000, -84.1000)
        self.ingest(rid(1, "2026-08-23T12:00:01Z", 34.0000, -84.0000))
        self.pose("2026-08-23T12:00:01.500000Z", 34.0900, -84.0900)
        output = self.ingest(rid(2, "2026-08-23T12:00:02Z", 34.0020, -84.0020))
        track = next(item["value"] for item in output if item["kind"] == "mobile_track_revision")
        self.assertEqual(track["points"][0]["latitude"], 34.0000)
        self.assertEqual(track["points"][1]["latitude"], 34.0020)
        self.assertNotEqual(track["points"][1]["latitude"], 34.0900)
        self.assertTrue(track["observer_pose_association_refs"])

    def test_malformed_remote_id_is_evidence_but_not_a_track(self):
        payload = rid(1, "2026-08-23T12:00:01Z", 34.0, -84.0)
        payload["validity"] = "MALFORMED"
        payload["aircraft_position"] = None
        output = self.ingest(payload)
        state = next(item for item in output if item["kind"] == "remote_id_evidence_state")
        self.assertEqual(state["validity"], "MALFORMED")
        self.assertFalse(state["track_updated"])
        self.assertNotIn("mobile_track_revision", [item["kind"] for item in output])

    def test_clock_contradiction_is_not_silently_added_to_track(self):
        self.ingest(rid(1, "2026-08-23T12:00:01Z", 34.0, -84.0))
        payload = rid(2, "2026-08-23T11:59:00Z", 34.01, -84.01)
        output = self.loop.ingest_remote_id(
            payload, received_at_utc="2026-08-23T12:00:02Z", host_monotonic_ns=2
        )
        self.assertIn("contradiction", [item["kind"] for item in output])
        state = next(item for item in output if item["kind"] == "remote_id_evidence_state")
        self.assertEqual(state["validity"], "CONTRADICTED")
        self.assertFalse(state["track_updated"])
        track = next(item["value"] for item in output if item["kind"] == "mobile_track_revision")
        self.assertEqual(track["motion_state"], "MIXED_OR_CONTRADICTED")

    def test_out_of_order_message_is_retained_as_contradiction_not_fused(self):
        self.ingest(rid(1, "2026-08-23T12:00:02Z", 34.0, -84.0))
        output = self.ingest(rid(2, "2026-08-23T12:00:01Z", 34.01, -84.01))
        self.assertIn("contradiction", [item["kind"] for item in output])
        track = next(item["value"] for item in output if item["kind"] == "mobile_track_revision")
        self.assertEqual(track["motion_state"], "MIXED_OR_CONTRADICTED")
        self.assertEqual(len(track["points"]), 1)

    def test_exact_duplicate_sequence_is_counted_and_not_reinserted(self):
        payload = rid(1, "2026-08-23T12:00:01Z", 34.0, -84.0)
        self.ingest(payload)
        duplicate = self.ingest(payload)
        self.assertEqual(duplicate, [{"kind": "duplicate_remote_id_input", "source_sequence": 1}])
        self.assertEqual(self.loop.duplicate_count, 1)

    def test_reused_sequence_with_different_content_is_rejected(self):
        self.ingest(rid(1, "2026-08-23T12:00:01Z", 34.0, -84.0))
        with self.assertRaisesRegex(ValueError, "reused"):
            self.ingest(rid(1, "2026-08-23T12:00:01Z", 34.1, -84.1))

    def test_remote_id_authentication_claim_is_not_promoted(self):
        payload = rid(1, "2026-08-23T12:00:01Z", 34.0, -84.0)
        payload["authentication_state"] = "VALID"
        output = self.ingest(payload)
        message = next(item["value"] for item in output if item["kind"] == "remote_id_message")
        self.assertEqual(message["authentication"]["verification"], "NOT_CHECKED")
        self.assertEqual(message["authentication"]["trust_anchor_state"], "UNKNOWN")

    def test_status_and_absence_never_create_aircraft_claim(self):
        output = self.loop.ingest_status({
            "event": "receiver_status", "state": "DEGRADED",
            "explicitly_lost_count": 3, "reason_codes": ["WIFI_SCAN_THROTTLED"],
        }, received_at_utc="2026-08-23T12:00:00Z")
        self.assertFalse(output[0]["absence_claim_permitted"])
        self.assertEqual(output[0]["value"]["explicitly_lost_count"], 3)
        self.assertFalse(self.loop.groups)

    def test_new_schemas_validate_emitted_events(self):
        self.ingest(rid(1, "2026-08-23T12:00:01Z", 34.0, -84.0))
        output = self.ingest(rid(2, "2026-08-23T12:00:02Z", 34.002, -84.002))
        mapping = {
            "remote_id_message": "remote_id_message.schema.json",
            "mobile_track_revision": "mobile_track.schema.json",
            "local_alert": "local_alert.schema.json",
            "node_revision": "node_estimate.schema.json",
            "evidence_receipt": "evidence_receipt.schema.json",
        }
        for item in output:
            schema_name = mapping.get(item["kind"])
            if schema_name:
                schema = json.loads((ROOT / "SCHEMAS" / schema_name).read_text())
                validate(item["value"], schema)


if __name__ == "__main__":
    unittest.main()
