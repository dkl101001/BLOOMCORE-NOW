from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flockoff.adapters.flock_you import normalize as normalize_flock_you
from flockoff.adapters.generic_passive import normalize_feature_record
from flockoff.adapters.remote_id import normalize as normalize_remote_id
from flockoff.canonical import canonical_bytes, sha256_uri, without_keys
from flockoff.cli import _load_jsonl
from flockoff.crypto import FieldCipher
from flockoff.export import (
    assert_route_safe, build_public_bundle, make_local_draft_approval,
    publication_request_digest,
)
from flockoff.hardware import absence_claim_allowed, require_capability
from flockoff.geometry import validate_region_geojson
from flockoff.ledger import EvidenceLedger
from flockoff.lineage import LineageGraph, SourceAssertion
from flockoff.receipts import make_receipt, verify_receipt
from flockoff.replay import make_pose, run_records
from flockoff.schema_guard import ValidationError, validate
from flockoff.signatures import signature_content_hash
from flockoff.signatures import evaluate

SECRET = bytes(range(32))
ROUTE_SECRET = bytes(reversed(range(32)))


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signature = read_json(ROOT / "SIGNATURES" / "candidate" / "flock_you_wifi_assertion_v0.1.0.json")
        cls.records = _load_jsonl(ROOT / "TESTS" / "synthetic_traces" / "fixed_two_pass.jsonl")
        cls.result = run_records(
            cls.records, signature=cls.signature, rotation_secret=SECRET,
            include_restricted=True,
        )

    def schema(self, name: str):
        return read_json(ROOT / "SCHEMAS" / name)

    def test_replay_is_deterministic(self):
        second = run_records(
            self.records, signature=self.signature, rotation_secret=SECRET,
            include_restricted=True,
        )
        self.assertEqual(canonical_bytes(self.result), canonical_bytes(second))
        self.assertTrue(verify_receipt(self.result["receipt"]))

    def test_all_replay_objects_validate(self):
        groups = {
            "observation.schema.json": self.result["observations"],
            "receiver_pose.schema.json": self.result["poses"],
            "signature_match.schema.json": self.result["signature_matches"],
            "pose_association.schema.json": self.result["pose_associations"],
            "pass_partition.schema.json": self.result["pass_partitions"],
            "measurement_lineage.schema.json": self.result["measurement_lineages"],
            "node_estimate.schema.json": [self.result["node_revision"]],
            "evidence_receipt.schema.json": self.result["receipts"],
        }
        for schema_name, items in groups.items():
            for item in items:
                validate(item, self.schema(schema_name))
        validate(self.signature, self.schema("signature.schema.json"))
        validate_region_geojson(self.result["node_revision"]["location"]["geojson"])
        self.assertEqual(self.signature["provenance"]["content_hash"], signature_content_hash(self.signature))

    def test_empty_or_open_inferred_geometry_fails(self):
        with self.assertRaises(ValueError):
            validate_region_geojson({"type": "Polygon", "coordinates": []})
        with self.assertRaises(ValueError):
            validate_region_geojson({"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]})

    def test_flock_you_adapter_minimizes_identifier_and_does_not_invent_features(self):
        payload = self.records[1]["payload"]
        observation = normalize_flock_you(
            payload,
            observed_at_utc="2026-08-22T00:00:00Z",
            ingested_at_utc="2026-08-22T00:00:00Z",
            receiver_id="rx",
            hardware_profile_id="profile",
            rotation_epoch="session",
            rotation_secret=SECRET,
        )
        encoded = canonical_bytes(observation).decode()
        self.assertNotIn(payload["mac_address"], encoded)
        self.assertEqual(observation["measurement"]["feature_hashes"], [])
        self.assertTrue(observation["provenance"]["raw_input_digest"].startswith("hmac-sha256:"))
        self.assertEqual(observation["emitter"]["address_randomization_state"], "LOCALLY_ADMINISTERED")
        self.assertFalse(observation["privacy"]["public_export_allowed"])
        wrong_band = dict(payload, protocol="wifi_5ghz")
        with self.assertRaises(ValueError):
            normalize_flock_you(
                wrong_band, observed_at_utc="2026-08-22T00:00:00Z",
                ingested_at_utc="2026-08-22T00:00:00Z", receiver_id="rx",
                hardware_profile_id="profile", rotation_epoch="session", rotation_secret=SECRET,
            )
        impossible = dict(payload, detection_tier=4, detection_method="wifi_oui_addr2")
        with self.assertRaises(ValueError):
            normalize_flock_you(
                impossible, observed_at_utc="2026-08-22T00:00:00Z",
                ingested_at_utc="2026-08-22T00:00:00Z", receiver_id="rx",
                hardware_profile_id="profile", rotation_epoch="session", rotation_secret=SECRET,
            )
        for contradictory in (
            dict(payload, oui="00:11:22"),
            dict(payload, frequency=2412),
            dict(payload, rssi=5),
        ):
            with self.assertRaises(ValueError):
                normalize_flock_you(
                    contradictory, observed_at_utc="2026-08-22T00:00:00Z",
                    ingested_at_utc="2026-08-22T00:00:00Z", receiver_id="rx",
                    hardware_profile_id="profile", rotation_epoch="session",
                    rotation_secret=SECRET,
                )

    def test_remote_id_received_is_not_authenticated_or_rf_only(self):
        payload = {
            "transport": "wifi_beacon",
            "validity": "VALID",
            "uas_id_type": "SERIAL_NUMBER",
            "uas_id": "TEST-RAW-ID",
            "aircraft_position": {"latitude": 36.0, "longitude": -86.0, "horizontal_accuracy_m": 10},
            "authentication_state": "NOT_PRESENT",
        }
        observation = normalize_remote_id(
            payload, observed_at_utc="2026-08-22T01:00:00Z",
            ingested_at_utc="2026-08-22T01:00:00Z", receiver_id="rx",
            hardware_profile_id="rid-replay", rotation_epoch="session", rotation_secret=SECRET,
        )
        self.assertEqual(observation["measurement"]["kind"], "REMOTE_ID_BROADCAST")
        self.assertEqual(observation["measurement"]["remote_id"]["authentication_state"], "NOT_PRESENT")
        self.assertEqual(observation["measurement"]["remote_id"]["aircraft_position_source"], "BROADCAST_REMOTE_ID")
        self.assertNotIn("TEST-RAW-ID", canonical_bytes(observation).decode())
        self.assertTrue(observation["measurement"]["payload_digest"].startswith("hmac-sha256:"))
        validate(observation, self.schema("observation.schema.json"))

    def test_remote_id_discards_operator_position_and_downgrades_auth_claim(self):
        payload = {
            "transport": "wifi_beacon",
            "validity": "VALID",
            "uas_id_type": "SERIAL_NUMBER",
            "uas_id": "TEST-RAW-ID",
            "operator_or_takeoff_position": {
                "latitude": 36.123456, "longitude": -86.654321,
                "horizontal_accuracy_m": 3,
            },
            "authentication_state": "VALID",
        }
        observation = normalize_remote_id(
            payload, observed_at_utc="2026-08-22T01:00:00Z",
            ingested_at_utc="2026-08-22T01:00:00Z", receiver_id="rx",
            hardware_profile_id="rid-replay", rotation_epoch="session",
            rotation_secret=SECRET,
        )
        remote = observation["measurement"]["remote_id"]
        self.assertIsNone(remote["operator_or_takeoff_position"])
        self.assertEqual(remote["authentication_state"], "NOT_CHECKED")
        encoded = canonical_bytes(observation)
        self.assertNotIn(b"36.123456", encoded)
        self.assertNotIn(b"-86.654321", encoded)

    def test_malformed_remote_id_does_not_invent_position(self):
        payload = read_json(ROOT / "TESTS" / "negative_controls" / "malformed_remote_id.json")
        payload.pop("expected")
        observation = normalize_remote_id(
            payload, observed_at_utc="2026-08-22T01:00:00Z",
            ingested_at_utc="2026-08-22T01:00:00Z", receiver_id="rx",
            hardware_profile_id="rid-replay", rotation_epoch="session", rotation_secret=SECRET,
        )
        remote = observation["measurement"]["remote_id"]
        self.assertEqual(remote["validity"], "MALFORMED")
        self.assertIsNone(remote["aircraft_position"])
        self.assertIsNone(remote["operator_or_takeoff_position"])

    def test_prefix_only_negative_control_does_not_match(self):
        control = read_json(ROOT / "TESTS" / "negative_controls" / "ordinary_shared_prefix.json")
        observation = normalize_flock_you(
            control["payload"], observed_at_utc="2026-08-22T00:00:00Z",
            ingested_at_utc="2026-08-22T00:00:00Z", receiver_id="rx",
            hardware_profile_id="profile", rotation_epoch="session", rotation_secret=SECRET,
        )
        match = evaluate(observation, self.signature)
        self.assertEqual(match["match_state"], control["expected_match_state"])
        self.assertEqual(match["claim_ceiling"], control["maximum_claim"])

    def test_lineage_five_mirrors_count_once(self):
        graph = LineageGraph()
        graph.add(SourceAssertion("osm-node-v7", "ORIGINAL"))
        for number in range(5):
            graph.add(SourceAssertion(f"mirror-{number}", "CONFIRMED_DERIVATIVE", ["osm-node-v7"]))
        graph.add(SourceAssertion("municipal-contract", "INDEPENDENT_CONFIRMED"))
        graph.add(SourceAssertion("unattributed-copy", "SUSPECTED_COMMON_ORIGIN"))
        lower, upper = graph.independence_bounds(
            [*(f"mirror-{number}" for number in range(5)), "municipal-contract", "unattributed-copy"]
        )
        self.assertEqual(lower, 2)
        self.assertEqual(upper, 3)

    def test_osm_revisions_retain_one_stable_object_root(self):
        control = read_json(ROOT / "TESTS" / "negative_controls" / "osm_revision_history.json")
        graph = LineageGraph()
        for assertion in control["assertions"]:
            graph.add(SourceAssertion(assertion["id"], assertion["relation"], assertion["parents"]))
        expected = control["expected_independence_bounds"]
        self.assertEqual(
            graph.independence_bounds(control["query_assertions"]),
            (expected["lower"], expected["upper"]),
        )

    def test_receipt_timestamp_is_not_in_deterministic_body(self):
        kwargs = dict(
            subject_ref="subject", input_refs=["a"], input_hashes=[sha256_uri({"a": 1})],
            algorithm_name="test", algorithm_version="1", parameters={"x": 1}, output={"y": 2},
            source_locks=[], code_revision="test-revision",
            code_digest=sha256_uri(b"test-code"),
        )
        self.assertEqual(make_receipt(**kwargs), make_receipt(**kwargs))

    def test_default_replay_result_is_route_free(self):
        result = run_records(self.records, signature=self.signature, rotation_secret=SECRET)
        self.assertNotIn("poses", result)
        self.assertEqual(result["pose_refs"], sorted(pose["pose_id"] for pose in self.result["poses"]))
        self.assertNotIn("RESTRICTED_ROUTE", canonical_bytes(result).decode())

    def test_route_is_encrypted_and_immutable(self):
        pose = make_pose({
            "receiver_id": "rx", "observed_at_utc": "2026-08-22T00:00:00Z",
            "latitude": 36.123456, "longitude": -86.654321, "source": "SYNTHETIC",
        }, id_secret=SECRET)
        with tempfile.TemporaryDirectory() as temporary:
            db = Path(temporary) / "ledger.sqlite"
            ledger = EvidenceLedger(
                db, ROOT / "SCHEMAS" / "migrations" / "0001_initial.sql",
                FieldCipher(ROUTE_SECRET), evidence_digest_secret=SECRET,
            )
            ledger.append_restricted_pose(pose)
            self.assertEqual(ledger.read_restricted_pose(pose["pose_id"]), pose)
            with self.assertRaises(sqlite3.DatabaseError):
                ledger.connection.execute(
                    "UPDATE restricted_pose_ciphertexts SET key_id='changed' WHERE pose_id=?", (pose["pose_id"],)
                )
            ledger.close()
            contents = db.read_bytes()
            self.assertNotIn(b"36.123456", contents)
            self.assertNotIn(b"latitude", contents)

    def test_full_replay_persists_with_resolved_evidence_and_migration_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            db = Path(temporary) / "ledger.sqlite"
            migration = ROOT / "SCHEMAS" / "migrations" / "0001_initial.sql"
            with EvidenceLedger(
                db, migration, FieldCipher(ROUTE_SECRET), evidence_digest_secret=SECRET,
            ) as ledger:
                for pose in self.result["poses"]:
                    ledger.append_restricted_pose(pose)
                groups = [
                    ("measurement_lineage", "measurement_lineage_id", self.result["measurement_lineages"]),
                    ("observation", "observation_id", self.result["observations"]),
                    ("signature_match", "match_id", self.result["signature_matches"]),
                    ("pose_association", "association_id", self.result["pose_associations"]),
                    ("pass_partition", "partition_id", self.result["pass_partitions"]),
                    ("evidence_receipt", "receipt_id", self.result["receipts"]),
                ]
                for kind, id_field, items in groups:
                    for item in items:
                        ledger.append_event(kind, item[id_field], item)
                digest = ledger.append_node_revision(self.result["node_revision"])
                self.assertTrue(digest.startswith("sha256:"))
                row = ledger.connection.execute(
                    "SELECT sql_sha256 FROM schema_migrations WHERE migration_id=?",
                    ("0001_initial_immutable_ledger",),
                ).fetchone()
                self.assertEqual(row[0], sha256_uri(migration.read_bytes()))

    def test_receipt_inputs_and_node_derivation_closure_are_enforced(self):
        with tempfile.TemporaryDirectory() as temporary:
            db = Path(temporary) / "ledger.sqlite"
            migration = ROOT / "SCHEMAS" / "migrations" / "0001_initial.sql"
            with EvidenceLedger(
                db, migration, FieldCipher(ROUTE_SECRET), evidence_digest_secret=SECRET,
            ) as ledger:
                for pose in self.result["poses"]:
                    ledger.append_restricted_pose(pose)
                groups = [
                    ("measurement_lineage", "measurement_lineage_id", self.result["measurement_lineages"]),
                    ("observation", "observation_id", self.result["observations"]),
                    ("signature_match", "match_id", self.result["signature_matches"]),
                    ("pose_association", "association_id", self.result["pose_associations"]),
                    ("pass_partition", "partition_id", self.result["pass_partitions"]),
                ]
                for kind, id_field, items in groups:
                    for item in items:
                        ledger.append_event(kind, item[id_field], item)

                observation = self.result["observations"][0]
                wrong_hash_receipt = make_receipt(
                    subject_ref="wrong-hash-control",
                    input_refs=[observation["observation_id"]],
                    input_hashes=[sha256_uri({"not": "the observation"})],
                    algorithm_name="negative_control", algorithm_version="1.0.0",
                    parameters={}, output={}, source_locks=[], code_revision="test",
                    code_digest=sha256_uri(b"test-code"),
                )
                with self.assertRaisesRegex(ValueError, "input hash mismatch"):
                    ledger.append_event(
                        "evidence_receipt", wrong_hash_receipt["receipt_id"],
                        wrong_hash_receipt,
                    )

                for receipt in self.result["receipts"]:
                    ledger.append_event("evidence_receipt", receipt["receipt_id"], receipt)

                node = self.result["node_revision"]
                node_body = without_keys(node, "receipt_id")
                empty_receipt = make_receipt(
                    subject_ref=f"{node['node_id']}:revision:1",
                    input_refs=[], input_hashes=[],
                    algorithm_name="node_revision_assembler", algorithm_version="1.0.0",
                    parameters={}, output=node_body, source_locks=[], code_revision="test",
                    code_digest=sha256_uri(b"test-code"),
                )
                ledger.append_event(
                    "evidence_receipt", empty_receipt["receipt_id"], empty_receipt
                )
                with self.assertRaisesRegex(ValueError, "complete derivation graph"):
                    ledger.append_node_revision({**node_body, "receipt_id": empty_receipt["receipt_id"]})

                foreign_receipt = make_receipt(
                    subject_ref=f"{node['node_id']}:revision:1",
                    input_refs=[observation["observation_id"]],
                    input_hashes=[sha256_uri(observation)],
                    algorithm_name="node_revision_assembler", algorithm_version="1.0.0",
                    parameters={}, output=node_body, source_locks=[], code_revision="test",
                    code_digest=sha256_uri(b"test-code"),
                )
                ledger.append_event(
                    "evidence_receipt", foreign_receipt["receipt_id"], foreign_receipt
                )
                with self.assertRaisesRegex(ValueError, "complete derivation graph"):
                    ledger.append_node_revision({**node_body, "receipt_id": foreign_receipt["receipt_id"]})

    def test_failed_migration_rolls_back_schema_and_custody_together(self):
        with tempfile.TemporaryDirectory() as temporary:
            schema_root = Path(temporary) / "SCHEMAS"
            migrations = schema_root / "migrations"
            migrations.mkdir(parents=True)
            migration = migrations / "failing.sql"
            migration.write_text(
                "CREATE TABLE schema_migrations ("
                "migration_id TEXT PRIMARY KEY, sql_sha256 TEXT NOT NULL, "
                "applied_at_utc TEXT NOT NULL);\n"
                "CREATE TABLE partially_applied (value INTEGER);\n"
                "INSERT INTO table_that_does_not_exist VALUES (1);\n",
                encoding="utf-8",
            )
            (schema_root / "migration_manifest.json").write_text(
                json.dumps({
                    "migrations": [{"id": "failing", "path": "migrations/failing.sql"}]
                }),
                encoding="utf-8",
            )
            db = Path(temporary) / "ledger.sqlite"
            with self.assertRaises(sqlite3.DatabaseError):
                EvidenceLedger(
                    db, migration, FieldCipher(ROUTE_SECRET), evidence_digest_secret=SECRET,
                )
            from contextlib import closing
            with closing(sqlite3.connect(db)) as connection:
                tables = {
                    row[0] for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
            self.assertNotIn("partially_applied", tables)
            self.assertNotIn("schema_migrations", tables)

    def test_migration_cannot_escape_host_transaction_control(self):
        prefix = (
            "CREATE TABLE schema_migrations ("
            "migration_id TEXT PRIMARY KEY, sql_sha256 TEXT NOT NULL, "
            "applied_at_utc TEXT NOT NULL); "
        )
        controls = {
            "commit_same_line": "/* same-line bypass */ COMMIT;",
            "rollback_after_comment": "-- comment-prefixed bypass\nROLLBACK;",
            "savepoint": "SAVEPOINT nested;",
            "release": "RELEASE nested;",
            "end_alias": "END;",
        }
        for name, control in controls.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                schema_root = Path(temporary) / "SCHEMAS"
                migrations = schema_root / "migrations"
                migrations.mkdir(parents=True)
                migration = migrations / "escape.sql"
                migration.write_text(
                    prefix + control
                    + " CREATE TABLE partially_applied (value INTEGER);"
                    + " INSERT INTO missing_table VALUES (1);",
                    encoding="utf-8",
                )
                (schema_root / "migration_manifest.json").write_text(
                    json.dumps({
                        "migrations": [{"id": "escape", "path": "migrations/escape.sql"}]
                    }),
                    encoding="utf-8",
                )
                db = Path(temporary) / "ledger.sqlite"
                with self.assertRaises(sqlite3.DatabaseError):
                    EvidenceLedger(
                        db, migration, FieldCipher(ROUTE_SECRET),
                        evidence_digest_secret=SECRET,
                    )
                from contextlib import closing
                with closing(sqlite3.connect(db)) as connection:
                    tables = {
                        row[0] for row in connection.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        ).fetchall()
                    }
                self.assertNotIn("partially_applied", tables)
                self.assertNotIn("schema_migrations", tables)

    def test_pose_association_rejects_stale_or_wrong_receiver(self):
        stale = deepcopy(self.records)
        stale[1]["observed_at_utc"] = "2026-08-22T12:00:10Z"
        with self.assertRaises(ValueError):
            run_records(stale, signature=self.signature, rotation_secret=SECRET)
        wrong = deepcopy(self.records)
        wrong[1]["receiver_id"] = "rx-other"
        with self.assertRaises(ValueError):
            run_records(wrong, signature=self.signature, rotation_secret=SECRET)

    def test_emitters_are_partitioned_before_match_and_localization(self):
        records = []
        for record in self.records:
            records.append(deepcopy(record))
            if record.get("kind") == "flock_you_detection":
                control = deepcopy(record)
                control["source_sequence"] = int(record["source_sequence"]) + 100
                control["payload"]["mac_address"] = "02:00:00:00:00:99"
                control["payload"]["oui"] = "02:00:00"
                control["payload"]["detection_method"] = "wifi_oui_addr2"
                control["payload"]["detection_tier"] = 2
                records.append(control)
        result = run_records(records, signature=self.signature, rotation_secret=SECRET)
        self.assertEqual(len(result["node_revisions"]), 2)
        self.assertEqual(
            sorted(node["claim_level"] for node in result["node_revisions"]),
            ["RF_ACTIVITY_PRESENT", "SIGNATURE_MATCH"],
        )
        observations_by_key = {}
        for observation in result["observations"]:
            observations_by_key.setdefault(
                observation["emitter"]["ephemeral_emitter_key"], set()
            ).add(observation["observation_id"])
        for node in result["node_revisions"]:
            referenced = {ref for ref in node["evidence_refs"] if ref.startswith("obs_")}
            self.assertIn(referenced, observations_by_key.values())

    def test_public_export_is_allowlist_projection(self):
        node = dict(self.result["node_revision"], publication_state="PUBLIC_CANDIDATE")
        args = dict(
            node_revisions=[node], public_evidence=[], receipt_ids=[node["receipt_id"]],
            aggregate_counts={"WIFI_80211": 8},
        )
        approval = make_local_draft_approval(
            request_digest=publication_request_digest(**args),
            approved_at_utc="2026-08-22T12:00:00Z", operator_confirmation=True,
        )
        bundle = build_public_bundle(**args, approval=approval)
        assert_route_safe(bundle)
        bundle["receiver_id"] = "leak"
        with self.assertRaises(ValueError):
            assert_route_safe(bundle)

    def test_hardware_and_coverage_fail_closed(self):
        profile = read_json(ROOT / "hardware_profiles" / "five_ghz_unbound.json")
        with self.assertRaises(RuntimeError):
            require_capability(profile, "WIFI_80211", "5_GHZ")
        self.assertFalse(absence_claim_allowed(
            {"state": "UNSUPPORTED", "protocols": [], "bands": [], "loss_count": 0},
            "WIFI_80211", "5_GHZ",
        ))

    def test_generic_adapter_cannot_self_assert_unverified_geometry(self):
        profile = {
            "schema_version": "1.0.0",
            "hardware_profile_id": "bench-passive",
            "status": "BENCH_VERIFIED",
            "receiver": {
                "manufacturer": "test", "model": "test",
                "driver_or_firmware": "test", "revision": "1",
            },
            "capabilities": [{
                "protocol": "WIFI_80211", "bands": ["2.4_GHZ"],
                "measurement_types": ["SPECTRUM_FEATURE"], "verified": True,
            }],
            "verification": {
                "verified_at_utc": "2026-08-22T00:00:00Z", "method": "fixture",
                "evidence_refs": ["fixture"],
            },
            "limitations": [],
        }
        payload = {
            "capture_mode": "PASSIVE_RECEIVE_ONLY", "protocol": "WIFI_80211",
            "band": "2.4_GHZ", "measurement_kind": "SPECTRUM_FEATURE",
            "capabilities": ["TDOA"],
        }
        with self.assertRaises(ValueError):
            normalize_feature_record(
                payload, observed_at_utc="2026-08-22T00:00:00Z",
                ingested_at_utc="2026-08-22T00:00:00Z", receiver_id="rx",
                hardware_profile=profile, rotation_epoch="session", rotation_secret=SECRET,
                trusted_hardware_profile=True,
            )
        valid = {
            "capture_mode": "PASSIVE_RECEIVE_ONLY", "protocol": "WIFI_80211",
            "band": "2.4_GHZ", "measurement_kind": "SPECTRUM_FEATURE",
            "capabilities": [], "bearing_deg": 90, "tdoa_seconds": 0.1,
            "feature_hashes": ["enumerable-feature"],
        }
        observation = normalize_feature_record(
            valid, observed_at_utc="2026-08-22T00:00:00Z",
            ingested_at_utc="2026-08-22T00:00:00Z", receiver_id="rx",
            hardware_profile=profile, rotation_epoch="session", rotation_secret=SECRET,
            trusted_hardware_profile=True,
        )
        self.assertIsNone(observation["measurement"]["bearing_deg"])
        self.assertIsNone(observation["measurement"]["tdoa_seconds"])
        self.assertTrue(observation["measurement"]["payload_digest"].startswith("hmac-sha256:"))
        self.assertNotIn("enumerable-feature", canonical_bytes(observation).decode())
        validate(observation, self.schema("observation.schema.json"))
        payload["measurement_kind"] = "RF_TDOA"
        payload["capabilities"] = []
        with self.assertRaises(ValueError):
            normalize_feature_record(
                payload, observed_at_utc="2026-08-22T00:00:00Z",
                ingested_at_utc="2026-08-22T00:00:00Z", receiver_id="rx",
                hardware_profile=profile, rotation_epoch="session", rotation_secret=SECRET,
                trusted_hardware_profile=True,
            )

    def test_strict_json_rejects_duplicate_keys_and_nan(self):
        with tempfile.TemporaryDirectory() as temporary:
            duplicate = Path(temporary) / "duplicate.jsonl"
            duplicate.write_text('{"kind":"pose","kind":"other"}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                _load_jsonl(duplicate)
            invalid = Path(temporary) / "nan.jsonl"
            invalid.write_text('{"value":NaN}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                _load_jsonl(invalid)

    def test_uncalibrated_probability_fails_schema(self):
        node = json.loads(json.dumps(self.result["node_revision"]))
        node["classification"]["probabilities"] = {"RF_PATTERN": 0.82}
        with self.assertRaises(ValidationError):
            validate(node, self.schema("node_estimate.schema.json"))

    def test_signature_cannot_activate_without_validation_packet(self):
        signature = json.loads(json.dumps(self.signature))
        signature["status"] = "ACTIVE"
        with self.assertRaises(ValidationError):
            validate(signature, self.schema("signature.schema.json"))

    def test_untrusted_signature_cannot_elevate_vendor_claim(self):
        observation = self.result["observations"][0]
        signature = deepcopy(self.signature)
        signature["status"] = "ACTIVE"
        signature["claim_ceiling"] = "VENDOR_ASSOCIATED"
        signature["validation"].update({
            "calibration_state": "EXTERNALLY_VALIDATED",
            "positive_physical_nodes": 2,
            "negative_control_count": 300,
            "false_positive_upper_95": 0.005,
            "leave_one_device_out": True,
            "validation_receipt_ref": "receipt_" + "a" * 40,
        })
        self.assertEqual(evaluate(observation, signature)["claim_ceiling"], "RF_PATTERN")


if __name__ == "__main__":
    unittest.main()
