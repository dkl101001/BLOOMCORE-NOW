from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flockoff.inference import Sample, localize_static, require_tdoa_timing
from flockoff.mobile import MobileTrack, TrackPoint, dock_hypothesis


class BattleCaseTests(unittest.TestCase):
    def test_duplicate_packets_do_not_collapse_region(self):
        samples = [
            Sample(36.0003, -86.0010, -67, "rx", "ew"),
            Sample(36.0003, -86.0003, -51, "rx", "ew"),
            Sample(36.0003, -85.9997, -51, "rx", "ew"),
            Sample(36.0003, -85.9990, -67, "rx", "ew"),
            Sample(35.9990, -86.0003, -67, "rx", "ns"),
            Sample(35.9997, -86.0003, -51, "rx", "ns"),
            Sample(36.0003, -86.0003, -51, "rx", "ns"),
            Sample(36.0010, -86.0003, -67, "rx", "ns"),
        ]
        once = localize_static(samples)
        duplicated = localize_static(samples + [samples[0]] * 10)
        self.assertEqual(once["geojson"], duplicated["geojson"])
        self.assertGreater(once["area_m2"], 0)
        self.assertIsNone(once["confidence_level"])
        self.assertFalse(once["diagnostics"]["public_prior_used"])
        self.assertEqual(duplicated["diagnostics"]["spatial_block_count"], len(samples))

    def test_pose_accuracy_expands_support_region(self):
        base = [
            Sample(36.0003, -86.0010, -67, "rx", "ew", 3),
            Sample(36.0003, -86.0003, -51, "rx", "ew", 3),
            Sample(36.0003, -85.9997, -51, "rx", "ew", 3),
            Sample(36.0003, -85.9990, -67, "rx", "ew", 3),
            Sample(35.9990, -86.0003, -67, "rx", "ns", 3),
            Sample(35.9997, -86.0003, -51, "rx", "ns", 3),
            Sample(36.0003, -86.0003, -51, "rx", "ns", 3),
            Sample(36.0010, -86.0003, -67, "rx", "ns", 3),
        ]
        uncertain = [Sample(
            item.latitude, item.longitude, item.rssi_dbm, item.receiver_id,
            item.pass_id, 1000,
        ) for item in base]
        precise_result = localize_static(base)
        uncertain_result = localize_static(uncertain)
        self.assertGreater(uncertain_result["area_m2"], precise_result["area_m2"] * 10)
        self.assertEqual(uncertain_result["diagnostics"]["max_pose_accuracy_m"], 1000)

    def test_uncalibrated_receivers_are_never_compared_directly(self):
        samples = [
            Sample(36.0003, -86.0010, -67, "rx-a", "p1"),
            Sample(36.0003, -86.0003, -51, "rx-a", "p1"),
            Sample(36.0003, -85.9997, -51, "rx-a", "p1"),
            Sample(36.0003, -85.9990, -67, "rx-a", "p1"),
            Sample(35.9990, -86.0003, -67, "rx-b", "p2"),
            Sample(35.9997, -86.0003, -51, "rx-b", "p2"),
            Sample(36.0003, -86.0003, -51, "rx-b", "p2"),
            Sample(36.0010, -86.0003, -67, "rx-b", "p2"),
        ]
        result = localize_static(samples)
        self.assertFalse(result["diagnostics"]["cross_receiver_comparisons"])
        self.assertEqual(result["method"], "RANK_RSSI_SUPPORT")

    def test_static_vs_mobile_not_claimed_from_one_rf_track(self):
        track = MobileTrack("rf-track", "RF_INFERRED")
        track.add(TrackPoint("2026-08-22T00:00:00Z", 36.0, -86.0, 50, "RF_INFERRED"))
        self.assertEqual(track.state(), "MOTION_UNRESOLVED")

    def test_remote_id_track_is_explicit_broadcast_basis(self):
        track = MobileTrack("rid-track", "BROADCAST_REMOTE_ID")
        track.add(TrackPoint("2026-08-22T00:00:00Z", 36.0, -86.0, 5, "BROADCAST_REMOTE_ID"))
        track.add(TrackPoint("2026-08-22T00:00:10Z", 36.001, -86.0, 5, "BROADCAST_REMOTE_ID"))
        self.assertEqual(track.state(), "MOBILE")
        with self.assertRaises(ValueError):
            track.add(TrackPoint("2026-08-22T00:00:20Z", 36.002, -86.0, 5, "RF_INFERRED"))

    def test_endpoints_alone_never_prove_dock(self):
        endpoints = [
            {"flight_id": "f1", "observed_at_utc": "2026-08-20T00:00:00Z", "latitude": 36.0, "longitude": -86.0},
            {"flight_id": "f2", "observed_at_utc": "2026-08-21T00:00:00Z", "latitude": 36.0001, "longitude": -86.0},
            {"flight_id": "f3", "observed_at_utc": "2026-08-22T00:00:00Z", "latitude": 36.0, "longitude": -86.0001},
        ]
        self.assertEqual(dock_hypothesis(endpoints, independent_fixed_evidence=False), "ENDPOINT_CLUSTER")
        self.assertEqual(dock_hypothesis(endpoints, independent_fixed_evidence=True), "PROBABLE_DOCK_OR_BASE")
        self.assertEqual(
            dock_hypothesis(endpoints, independent_fixed_evidence=False, official_document_ref="municipal-contract"),
            "DOCUMENTED_DOCK_OR_BASE",
        )

    def test_tdoa_rejects_host_scale_timing(self):
        with self.assertRaises(RuntimeError):
            require_tdoa_timing(1e-6, 30.0)
        require_tdoa_timing(1e-8, 30.0)


if __name__ == "__main__":
    unittest.main()
