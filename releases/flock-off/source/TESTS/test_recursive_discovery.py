from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flockoff.recursive import (
    advance_campaign,
    detect_signature_drift,
    make_failure_packet,
    open_discovery_campaign,
    validation_decision,
)
from flockoff.schema_guard import validate


class RecursiveDiscoveryTests(unittest.TestCase):
    def schema(self, name: str):
        return json.loads((ROOT / "SCHEMAS" / name).read_text())

    def failure(self):
        return make_failure_packet(
            target_asset_ref="asset:adversarial-condor-like-fixture",
            failed_expectation="known 2.4 GHz Flock-associated signature",
            observation_refs=["obs_aaaaaaaaaaaaaaaa"],
            coverage_refs=["coverage_2g4_complete_fixture"],
            failed_assumption="same-vendor products inherit Falcon-like RF behavior",
            rationale="Target is independently established for the fixture, but the expected signature did not appear under bounded coverage.",
            next_test_seed="characterize additional passive emission surfaces and component topology",
            observed_at_utc="2026-08-23T15:00:00Z",
        )

    def test_detector_miss_becomes_failure_packet_not_absence(self):
        failure = self.failure()
        self.assertFalse(failure["absence_claim_permitted"])
        self.assertNotIn("UNKNOWN", failure.values())
        validate(failure, self.schema("failure_packet.schema.json"))

    def test_failure_opens_nonterminal_hunt(self):
        campaign = open_discovery_campaign(
            self.failure(),
            next_tests=["inspect a wider passive receive aperture", "test matched control sites"],
            opened_at_utc="2026-08-23T15:01:00Z",
        )
        self.assertEqual(campaign["state"], "HUNTING")
        self.assertTrue(campaign["next_tests"])
        validate(campaign, self.schema("discovery_campaign.schema.json"))

    def test_recursive_path_reaches_validation_only_through_controls_and_replication(self):
        campaign = open_discovery_campaign(
            self.failure(), next_tests=["collect candidate feature"],
            opened_at_utc="2026-08-23T15:01:00Z",
        )
        campaign = advance_campaign(
            campaign, new_state="CANDIDATE_SIGNATURE", evidence_refs=["capture-a"],
            next_tests=["run negative controls"], updated_at_utc="2026-08-23T15:02:00Z",
            known_features=["candidate timing feature"], signature_refs=["sig:candidate:1"],
            claim_ceiling="RF_PATTERN",
        )
        campaign = advance_campaign(
            campaign, new_state="CONTROL_TESTING", evidence_refs=["control-set-a"],
            next_tests=["replicate at independent site"], updated_at_utc="2026-08-23T15:03:00Z",
        )
        campaign = advance_campaign(
            campaign, new_state="REPLICATION_PENDING", evidence_refs=["control-pass-a"],
            next_tests=["replication site 2"], updated_at_utc="2026-08-23T15:04:00Z",
        )
        campaign = advance_campaign(
            campaign, new_state="VALIDATED", evidence_refs=["replication-pass-b"],
            next_tests=[], updated_at_utc="2026-08-23T15:05:00Z",
        )
        self.assertEqual(campaign["state"], "VALIDATED")
        self.assertEqual(campaign["revision"], 5)
        validate(campaign, self.schema("discovery_campaign.schema.json"))

    def test_illegal_shortcut_to_validated_is_rejected(self):
        campaign = open_discovery_campaign(
            self.failure(), next_tests=["collect candidate feature"],
            opened_at_utc="2026-08-23T15:01:00Z",
        )
        with self.assertRaisesRegex(ValueError, "illegal discovery transition"):
            advance_campaign(
                campaign, new_state="VALIDATED", evidence_refs=["one-hit"], next_tests=[],
                updated_at_utc="2026-08-23T15:02:00Z",
            )

    def test_insufficient_aperture_must_recurse(self):
        campaign = open_discovery_campaign(
            self.failure(), next_tests=["widen receive aperture"],
            opened_at_utc="2026-08-23T15:01:00Z",
        )
        campaign = advance_campaign(
            campaign, new_state="SENSING_APERTURE_INSUFFICIENT", evidence_refs=["coverage-gap"],
            next_tests=["bind receiver profile covering unresolved band"],
            updated_at_utc="2026-08-23T15:02:00Z",
        )
        validate(campaign, self.schema("discovery_campaign.schema.json"))
        campaign = advance_campaign(
            campaign, new_state="HUNTING", evidence_refs=["new-receiver-profile"],
            next_tests=["repeat matched target/control capture"],
            updated_at_utc="2026-08-23T15:03:00Z",
        )
        self.assertEqual(campaign["state"], "HUNTING")

    def test_drift_requires_adequate_coverage_before_reactivating_discovery(self):
        weak = detect_signature_drift(
            target_asset_ref="asset:fixture", signature_ref="sig:known:v1",
            prior_match_refs=["match-old"], current_match_refs=["match-new"],
            current_match_states=["NO_MATCH"], coverage_refs=["partial-coverage"],
            coverage_adequate=False, independent_miss_count=1,
            observed_at_utc="2026-08-23T16:00:00Z",
        )
        self.assertEqual(weak["drift_state"], "INSUFFICIENT_COVERAGE")
        self.assertEqual(weak["required_action"], "RETEST_WITH_COMPLETE_COVERAGE")
        validate(weak, self.schema("drift_event.schema.json"))

        strong = detect_signature_drift(
            target_asset_ref="asset:fixture", signature_ref="sig:known:v1",
            prior_match_refs=["match-old"], current_match_refs=["miss-a", "miss-b"],
            current_match_states=["NO_MATCH", "NO_MATCH"], coverage_refs=["coverage-a", "coverage-b"],
            coverage_adequate=True, independent_miss_count=2,
            observed_at_utc="2026-08-23T16:10:00Z",
        )
        self.assertEqual(strong["drift_state"], "CONFIRMED_DRIFT")
        self.assertEqual(strong["required_action"], "DEGRADE_SIGNATURE_AND_REACTIVATE_DISCOVERY")
        self.assertFalse(strong["absence_claim_permitted"])
        validate(strong, self.schema("drift_event.schema.json"))

    def test_validation_gate_does_not_invent_probability(self):
        recurse = validation_decision(
            candidate_signature_ref="sig:candidate:1", positive_physical_nodes=1,
            negative_control_count=10, false_positive_count=0, independent_replication_sites=0,
            contradiction_refs=[], evidence_refs=["capture-a"],
            evaluated_at_utc="2026-08-23T17:00:00Z",
        )
        self.assertEqual(recurse["decision"], "RECURSE")
        self.assertIsNone(recurse["probability"])
        validate(recurse, self.schema("validation_decision.schema.json"))

        advance = validation_decision(
            candidate_signature_ref="sig:candidate:1", positive_physical_nodes=2,
            negative_control_count=30, false_positive_count=0, independent_replication_sites=1,
            contradiction_refs=[], evidence_refs=["capture-a", "controls", "replication"],
            evaluated_at_utc="2026-08-23T17:10:00Z",
        )
        self.assertEqual(advance["decision"], "ADVANCE_TO_FIELD_TESTING")
        self.assertIsNone(advance["probability"])
        validate(advance, self.schema("validation_decision.schema.json"))

    def test_asset_ontology_forbids_cross_product_rf_inheritance(self):
        asset = {
            "schema_version":"1.1.0",
            "asset_id":"flock-condor-adversarial-seed",
            "vendor":"Flock Safety",
            "product_family":"Condor",
            "model_or_sku":None,
            "hardware_revision":None,
            "firmware_era":None,
            "region":"US",
            "deployment_form":"FIXED",
            "component_roles":["VIDEO_CAPTURE","ALPR_RECOGNITION"],
            "emitter_surfaces":[
                {"surface":"WIFI_2_4","state":"UNKNOWN","evidence_refs":[]},
                {"surface":"BLUETOOTH_LE","state":"UNKNOWN","evidence_refs":[]},
                {"surface":"CELLULAR","state":"UNKNOWN","evidence_refs":[]}
            ],
            "inheritance_policy":"NO_CROSS_PRODUCT_OR_REVISION_RF_INHERITANCE",
            "evidence_refs":[],
            "status":"SEED"
        }
        validate(asset, self.schema("surveillance_asset.schema.json"))
        self.assertNotEqual(asset["emitter_surfaces"][0]["state"], "VERIFIED_PRESENT")


if __name__ == "__main__":
    unittest.main()
