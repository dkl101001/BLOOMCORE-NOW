from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flockoff.adapters.flock_you import normalize as normalize_flock_you
from flockoff.export import (
    assert_route_safe,
    build_public_bundle,
    make_local_draft_approval,
    publication_request_digest,
)
from flockoff.schema_guard import ValidationError, validate


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class PublicationPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        records = [json.loads(line) for line in (ROOT / "TESTS" / "synthetic_traces" / "fixed_two_pass.jsonl").read_text().splitlines()]
        payload = next(record["payload"] for record in records if record["kind"] == "flock_you_detection")
        cls.observation = normalize_flock_you(
            payload,
            observed_at_utc="2026-08-22T00:00:00Z",
            ingested_at_utc="2026-08-22T00:00:00Z",
            receiver_id="rx",
            hardware_profile_id="profile",
            rotation_epoch="session",
            rotation_secret=bytes(range(32)),
        )
        cls.node = read_json(ROOT / "SCHEMAS" / "examples" / "node_estimate.json")
        cls.node["publication_state"] = "PUBLIC_CANDIDATE"
        cls.public_evidence = [{
            "schema_version": "1.0.0",
            "evidence_id": "pub_" + "1" * 40,
            "source_id": "municipal-record-1",
            "source_lineage_id": "municipal-record-1",
            "parent_source_ids": [],
            "source_type": "MUNICIPAL_RECORD",
            "authority_role": "DOCUMENTARY_EVIDENCE",
            "independence_class": "ORIGINAL",
            "retrieved_at_utc": "2026-08-22T00:00:00Z",
            "claim": {
                "claim_type": "DEPLOYMENT_RECORD",
                "claim_text": "A public record describes a candidate node.",
                "geometry": {"type": "Point", "coordinates": [-86.0, 36.0]},
                "coordinate_uncertainty_m": 25.0,
            },
            "license_or_terms": "Public record; custody review required",
            "provenance": {
                "source_locator": "https://example.gov/records/1",
                "content_hash": "sha256:" + "2" * 64,
                "transform_version": "test-1",
            },
        }]

    def schema(self, name: str):
        return read_json(ROOT / "SCHEMAS" / name)

    def build_args(self):
        return {
            "node_revisions": [copy.deepcopy(self.node)],
            "public_evidence": copy.deepcopy(self.public_evidence),
            "receipt_ids": [self.node["receipt_id"]],
            "aggregate_counts": {"PUBLIC_RECORD": 1, "WIFI_80211": 8},
        }

    def approval_for(self, args):
        request_digest = publication_request_digest(**args)
        return make_local_draft_approval(
            request_digest=request_digest,
            approved_at_utc="2026-08-22T12:00:00Z",
            operator_confirmation=True,
        )

    def test_operational_observation_privacy_is_schema_enforced(self):
        schema = self.schema("observation.schema.json")
        validate(self.observation, schema)
        mutations = []

        raw_retained = copy.deepcopy(self.observation)
        raw_retained["privacy"]["raw_retained"] = True
        mutations.append(raw_retained)

        target_identifier = copy.deepcopy(self.observation)
        target_identifier["emitter"]["target_identifier"] = "00:11:22:33:44:55"
        target_identifier["emitter"]["identifier_retention"] = "TARGET_RELEVANT"
        mutations.append(target_identifier)

        plain_digest = copy.deepcopy(self.observation)
        plain_digest["provenance"]["raw_input_digest"] = "sha256:" + "0" * 64
        mutations.append(plain_digest)

        raw_capture = copy.deepcopy(self.observation)
        raw_capture["provenance"]["raw_capture_ref"] = "file:///private/capture.pcap"
        mutations.append(raw_capture)

        unknown_extension = copy.deepcopy(self.observation)
        unknown_extension["measurement"]["extensions"]["raw_packet"] = "secret"
        mutations.append(unknown_extension)

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValidationError):
                    validate(mutation, schema)

    def test_raw_observation_can_never_be_marked_for_public_export(self):
        schema = self.schema("observation.schema.json")
        for privacy_class in ("OPERATIONAL_MINIMIZED", "EPHEMERAL", "RESEARCH_RAW"):
            observation = copy.deepcopy(self.observation)
            observation["privacy"]["class"] = privacy_class
            observation["privacy"]["public_export_allowed"] = True
            with self.subTest(privacy_class=privacy_class):
                with self.assertRaises(ValidationError):
                    validate(observation, schema)
        for forbidden_class in ("PUBLIC_EXPORT", "RESTRICTED_ROUTE"):
            observation = copy.deepcopy(self.observation)
            observation["privacy"]["class"] = forbidden_class
            with self.subTest(forbidden_class=forbidden_class):
                with self.assertRaises(ValidationError):
                    validate(observation, schema)

    def test_bundle_requires_exact_explicit_local_approval(self):
        args = self.build_args()
        with self.assertRaises(ValueError):
            build_public_bundle(**args)
        with self.assertRaises(ValueError):
            make_local_draft_approval(
                request_digest=publication_request_digest(**args),
                approved_at_utc="2026-08-22T12:00:00Z",
                operator_confirmation=False,
            )

        approval = self.approval_for(args)
        validate(approval, self.schema("publication_approval.schema.json"))
        bundle = build_public_bundle(**args, approval=approval)
        validate(bundle, self.schema("export_bundle.schema.json"))
        assert_route_safe(bundle)
        self.assertEqual(bundle["review_state"], "LOCAL_DRAFT")
        self.assertEqual(bundle["publication_approval"]["scope"], "LOCAL_DRAFT_ONLY")

    def test_approval_is_bound_to_exact_projection(self):
        args = self.build_args()
        approval = self.approval_for(args)
        changed = self.build_args()
        changed["aggregate_counts"]["WIFI_80211"] = 9
        with self.assertRaises(ValueError):
            build_public_bundle(**changed, approval=approval)

        tampered = copy.deepcopy(approval)
        tampered["acknowledgements"]["contradictions_preserved"] = False
        with self.assertRaises(ValueError):
            build_public_bundle(**args, approval=tampered)

    def test_nested_public_projection_is_closed(self):
        args = self.build_args()
        bundle = build_public_bundle(**args, approval=self.approval_for(args))
        export_schema = self.schema("export_bundle.schema.json")

        node_leak = copy.deepcopy(bundle)
        node_leak["nodes"][0]["receiver_id"] = "rx-route-link"
        with self.assertRaises(ValidationError):
            validate(node_leak, export_schema)
        with self.assertRaises(ValueError):
            assert_route_safe(node_leak)

        evidence_leak = copy.deepcopy(bundle)
        evidence_leak["public_evidence"][0]["claim"]["operator_or_takeoff_position"] = {
            "latitude": 36.0, "longitude": -86.0,
        }
        with self.assertRaises(ValidationError):
            validate(evidence_leak, export_schema)
        with self.assertRaises(ValueError):
            assert_route_safe(evidence_leak)

        broadened = copy.deepcopy(bundle)
        broadened["review_state"] = "PUBLISHED"
        with self.assertRaises(ValidationError):
            validate(broadened, export_schema)
        with self.assertRaises(ValueError):
            assert_route_safe(broadened)

    def test_non_allowlisted_claim_is_rejected_before_projection(self):
        args = self.build_args()
        args["public_evidence"][0]["claim"]["local_path"] = "/private/source.json"
        with self.assertRaises(ValueError):
            publication_request_digest(**args)

    def test_internal_evidence_references_are_not_public_projection_fields(self):
        args = self.build_args()
        public_id = args["public_evidence"][0]["evidence_id"]
        args["node_revisions"][0]["evidence_refs"].append(public_id)
        bundle = build_public_bundle(**args, approval=self.approval_for(args))
        public_node = bundle["nodes"][0]
        self.assertEqual(public_node["public_evidence_refs"], [public_id])
        self.assertNotIn("evidence_refs", public_node)
        encoded = json.dumps(public_node, sort_keys=True)
        for internal_prefix in ("obs_", "match_", "assoc_", "mlineage_", "partition_"):
            self.assertNotIn(internal_prefix, encoded)

        unknown = self.build_args()
        unknown["node_revisions"][0]["evidence_refs"].append("pub_" + "f" * 40)
        with self.assertRaises(ValueError):
            publication_request_digest(**unknown)

    def test_unlicensed_public_evidence_is_rejected_before_approval(self):
        for license_or_terms in (None, "", "   "):
            args = self.build_args()
            args["public_evidence"][0]["license_or_terms"] = license_or_terms
            with self.subTest(license_or_terms=license_or_terms):
                with self.assertRaises(ValueError):
                    publication_request_digest(**args)


if __name__ == "__main__":
    unittest.main()
