# SPDX-License-Identifier: MPL-2.0
"""Synthetic plumbing only: the byte fixtures are NOT models or empirical trials."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.pipeline import analyze, blind, classify, factorial_effects, lock, validate_scores
from runner.core import (
    ROOT,
    digest,
    expected_cells,
    plan,
    prompt,
    read,
    route,
    run,
    stamp,
    validate_record,
    verify_checkpoint,
    verify_run,
    write,
)


def checkpoint(root, payload=b"TEST_FIXTURE_NOT_MODEL_WEIGHTS"):
    root.mkdir(parents=True, exist_ok=True)
    (root / "fixture.bin").write_bytes(payload)
    files = {"fixture.bin": hashlib.sha256(payload).hexdigest()}
    return {
        "root": str(root.resolve()),
        "files": files,
        "weights_files": ["fixture.bin"],
        "sha256": digest(files),
        "state_kind": "weights",
    }


class FixtureAdapter:
    """Never exported as a model adapter: returns declared fixture text/bytes."""

    def __init__(self):
        self.requests = []

    def call(self, req):
        self.requests.append(copy.deepcopy(req))
        reply = {
            "provider": "TEST_FIXTURE",
            "model": "NOT_A_MODEL",
            "model_version": "fixture-1",
            "provenance": {"kind": "TEST_FIXTURE_NOT_EMPIRICAL"},
        }
        if req["operation"] == "infer":
            reply.update(
                raw_response='{"action":"allocate_q","accept_component":false,"explanation":"TEST_FIXTURE_NOT_EMPIRICAL"}',
                checkpoint_sha256=req["checkpoint"]["sha256"],
                effective_parameters=req["inference_parameters"],
                isolation="fresh_session_no_external_state",
            )
        else:
            parent = req["parent_checkpoint"]
            payload = (Path(parent["root"]) / "fixture.bin").read_bytes() + str(
                len(self.requests)
            ).encode()
            reply.update(
                checkpoint=checkpoint(Path(req["output_directory"]), payload),
                parent_checkpoint_sha256=parent["sha256"],
                objective_sha256=req["training_spec"]["objective_sha256"],
                steps=req["training_spec"]["steps"],
                optimizer_reset=True,
                training_metrics={"fixture_only": True, "actual_tokens": 0},
            )
        return reply


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = read(ROOT / "CONTROLS/example.json")
        self.config.update(
            provider="TEST_FIXTURE",
            model="NOT_A_MODEL",
            base_checkpoint=checkpoint(self.root / "base"),
        )
        self.config["training"]["objective_sha256"] = digest("fixture objective")

    def fixture_run(self):
        adapter = FixtureAdapter()
        out = self.root / "run"
        result = run(self.config, out, adapter)
        return out, adapter, result

    def scored(self):
        out, _adapter, _result = self.fixture_run()
        public = self.root / "public"
        private = self.root / "private"
        blind(out, public, private)
        entries = read(public / "responses.json")
        scores = read(public / "ratings_template.json")
        filled = []
        for row in scores["ratings"]:
            e = next(e for e in entries if e["blind_id"] == row["blind_id"])
            for name in ("rater-1", "rater-2"):
                r = copy.deepcopy(row)
                r["rater_id"] = name
                r["scores"] = {d: 1 for d in r["scores"]}
                r["evidence"] = {d: "TEST_FIXTURE_NOT_EMPIRICAL" for d in r["scores"]}
                r["choice"] = "OTHER" if e["actions"] else None
                for d in r["open_codes"]:
                    r["open_codes"][d] = {
                        "status": "UNSCORABLE",
                        "evidence": "fixture text",
                        "counterevidence": "No real inference occurred.",
                    }
                filled.append(r)
        scores["ratings"] = filled
        write(self.root / "ratings.json", scores)
        return public, private, scores

    def test_pilot_plan_and_explicit_non_run(self):
        c = read(ROOT / "CONTROLS/example.json")
        result = run(c, self.root / "unavailable")
        self.assertEqual(result["status"], "MODEL_TRIALS_NOT_RUN")
        self.assertEqual(plan(c)["probe_calls"], 222)
        self.assertEqual(plan(c)["training_interaction_calls"], 22)
        self.assertEqual(len(expected_cells(c)), 222)
        c["cycles"] = 3
        self.assertEqual(plan(c)["probe_calls"], 282)

    def test_complete_lineage_neutral_isolation_and_ablation(self):
        out, adapter, result = self.fixture_run()
        records = verify_run(out)
        self.assertEqual(result["completed_probes"], 222)
        self.assertEqual(len(adapter.requests), 257)
        sessions = [r["session_id"] for r in adapter.requests if r["operation"] == "infer"]
        self.assertEqual(len(sessions), len(set(sessions)))
        for r in records:
            if r["context"] == "neutral":
                self.assertEqual(len(r["messages"]), 1)
                self.assertIsNone(r["component_sha256"])
        ablation = [r for r in records if r["phase"] == "ablation"]
        self.assertEqual(len({r["checkpoint_sha256"] for r in ablation}), 1)
        self.assertEqual(len({r["component_sha256"] for r in ablation if r["regime"] != "0"}), 1)
        parent = read(out / "transitions/H-0-1.json")["child"]
        self.assertEqual(read(out / "transitions/H_to_E-0-2.json")["parent"], parent)
        probes = read(ROOT / "PROBES/probes.json")["probes"]
        for req in adapter.requests:
            if req["operation"] == "train":
                text = json.dumps(req["episodes"])
                for p in probes:
                    self.assertNotIn(p["facts"], text)
                self.assertNotIn("evaluator_scores", req)
                for ep in req["episodes"]:
                    self.assertNotIn("routing", ep)
                    self.assertNotIn("regime", ep)
                    self.assertNotIn("wording", ep)
                    self.assertNotIn("inference_event", ep)
                    self.assertIn("executed_action", ep)

    def test_reverse_direction_supported(self):
        self.config["reversal"] = "E_to_H"
        out, _, _ = self.fixture_run()
        self.assertEqual(len(verify_run(out)), 222)
        self.assertEqual(
            read(out / "transitions/E_to_H-0-2.json")["parent"],
            read(out / "transitions/E-0-1.json")["child"],
        )

    def test_replicates_use_matched_but_distinct_training_seeds(self):
        self.config["replicates"] = 2
        out, adapter, _result = self.fixture_run()
        self.assertEqual(len(verify_run(out)), 444)
        seeds = [r["training_spec"]["seed"] for r in adapter.requests if r["operation"] == "train"]
        self.assertEqual(seeds.count(self.config["training"]["seed"]), 11)
        self.assertEqual(seeds.count(self.config["training"]["seed"] + 1), 11)

    def test_choice_inversion_detects_switch_with_unchanged_rubric_scores(self):
        public, private, scores = self.scored()
        key = read(private / "key.json")["records"]
        for row in scores["ratings"]:
            record = key[row["blind_id"]]
            if record["probe_id"] == "P01":
                row["choice"] = "A" if record["variant"] == "E_A" else "B"
        (self.root / "ratings.json").write_text(json.dumps(scores))
        lock(public, self.root / "ratings.json")
        analyze(public, private, self.root / "choices.json")
        report = read(self.root / "choices.json")
        for row in report["OBSERVED"]["evaluator_inversion"]:
            self.assertEqual(row["choice_distances"]["E_A-E_B"], 1)
            self.assertEqual(row["distances"]["E_A-E_B"], 0)
        self.assertEqual(len(report["OBSERVED"]["evaluator_dependence_contrasts"]), 8)

    def test_crossed_training_holds_wording_while_executing_different_rules(self):
        out, _, _ = self.fixture_run()
        for left, right in (("H", "E_W_H"), ("H_W_E", "E")):
            a = read(out / f"transitions/{left}-0-1.json")
            b = read(out / f"transitions/{right}-0-1.json")
            self.assertEqual(a["parent"], b["parent"])
            self.assertEqual(a["wording"], b["wording"])
            self.assertEqual(a["episodes"][0]["messages"], b["episodes"][0]["messages"])
            self.assertEqual(a["episodes"][0]["raw_response"], b["episodes"][0]["raw_response"])
            self.assertEqual(a["episodes"][0]["routing"]["executed_action"], "allocate_p")
            self.assertEqual(b["episodes"][0]["routing"]["executed_action"], "allocate_q")
            self.assertNotEqual(a["episodes"][0]["outcome"], b["episodes"][0]["outcome"])
        self.assertEqual(len(verify_run(out)), 222)

    def test_reversal_keeps_wording_fixed(self):
        for direction in ("H_to_E", "E_to_H"):
            with self.subTest(direction=direction):
                c = copy.deepcopy(self.config)
                c["reversal"] = direction
                out = self.root / direction
                run(c, out, FixtureAdapter())
                source, target = direction.split("_to_")
                t = read(out / f"transitions/{direction}-0-2.json")
                self.assertEqual((t["regime"], t["wording"]), (target, source))
                for r in verify_run(out):
                    if r["branch"] == direction:
                        self.assertEqual(r["wording"], source)

    def test_paired_route_ablation_preserves_model_proposal(self):
        out, _, _ = self.fixture_run()
        traces = [read(p) for p in (out / "routing_ablation").glob("*.json")]
        self.assertEqual(len(traces), 4)
        for w in ("H", "E"):
            pair = [t for t in traces if t["wording"] == w]
            for key in ("event_sha256", "checkpoint_sha256", "component_sha256", "raw_response"):
                self.assertEqual(len({t[key] for t in pair}), 1)
            self.assertEqual(
                {t["routing"]["executed_action"] for t in pair}, {"allocate_p", "allocate_q"}
            )
            self.assertTrue(
                all(t["evidence_class"] == "PAIRED_ROUTE_REPLAY_NOT_LEARNED_EFFECT" for t in pair)
            )

    def test_wrong_wording_rejected_with_recomputed_receipt(self):
        out, _, _ = self.fixture_run()
        p = next((out / "records").glob("*.json"))
        r = read(p)
        r["wording"] = "E" if r["wording"] != "E" else "H"
        p.write_text(json.dumps(stamp(r)))
        with self.assertRaisesRegex(ValueError, "factor assignment"):
            verify_run(out)

    def test_tampered_execution_rejected(self):
        out, _, _ = self.fixture_run()
        p = next((out / "routing_ablation").glob("*.json"))
        r = read(p)
        r["outcome"] = {"p": 99, "q": 99}
        p.write_text(json.dumps(stamp(r)))
        with self.assertRaisesRegex(ValueError, "execution mismatch"):
            verify_run(out)

    def test_factorial_separates_wording_topology_and_interaction(self):
        cases = [
            ({"H": 1, "H_W_E": 1, "E_W_H": 0, "E": 0}, (1, 0, 0)),
            ({"H": 1, "H_W_E": 0, "E_W_H": 1, "E": 0}, (0, 1, 0)),
            ({"H": 1, "H_W_E": -1, "E_W_H": -1, "E": 1}, (0, 0, 4)),
            ({"H": 0, "H_W_E": 0, "E_W_H": 0, "E": 0}, (0, 0, 0)),
        ]
        for cells, expected in cases:
            with self.subTest(cells=cells):
                actual = factorial_effects(cells)
                self.assertEqual(
                    tuple(actual[k] for k in ("topology", "wording", "interaction")), expected
                )
        self.assertTrue(
            all(
                v is None
                for v in factorial_effects({"H": None, "H_W_E": 1, "E_W_H": 0, "E": 0}).values()
            )
        )
        with self.assertRaisesRegex(ValueError, "complete crossed"):
            factorial_effects({"H": 1, "E": 0})

    def test_scored_topology_effect_survives_factorial_analysis(self):
        public, private, scores = self.scored()
        key = read(private / "key.json")["records"]
        for row in scores["ratings"]:
            r = key[row["blind_id"]]
            if r["phase"] == "main" and r["generation"] > 0:
                row["scores"] = {d: (2 if r["regime"] == "H" else 0) for d in row["scores"]}
        (self.root / "ratings.json").write_text(json.dumps(scores))
        lock(public, self.root / "ratings.json")
        analyze(public, private, self.root / "factorial.json")
        report = read(self.root / "factorial.json")["OBSERVED"]
        rows = [
            r
            for r in report["factorial_effects"]
            if not r["dimension"].startswith("evaluator_dependence")
        ]
        self.assertTrue(rows)
        for r in rows:
            self.assertEqual(r["neutral_change"]["topology"], 1)
            self.assertEqual(r["neutral_change"]["wording"], 0)
            self.assertEqual(r["neutral_change"]["interaction"], 0)
        self.assertEqual(len(report["paired_routing_ablation"]), 4)
        self.assertEqual(len(report["training_execution_traces"]), 11)
        for e in read(public / "responses.json"):
            self.assertNotIn("wording", e)
            self.assertNotIn("regime", e)

    def test_actual_admission_rules(self):
        proposal = read(ROOT / "REGIMES/topologies.json")["component"]
        subject = '{"action":"allocate_q","accept_component":false}'
        self.assertEqual(route("H", subject, proposal)["executed_action"], "allocate_p")
        self.assertEqual(route("E", subject, proposal)["executed_action"], "allocate_q")
        self.assertEqual(route("0", subject, proposal)["executed_action"], "allocate_q")
        self.assertEqual(
            route("E", subject.replace("false", "true"), proposal)["executed_action"], "allocate_p"
        )
        self.assertEqual(route("E", "not JSON", proposal)["executed_action"], "OTHER")
        self.assertEqual(
            route("E", '{"accept_component":"true"}', proposal)["executed_action"], "OTHER"
        )

    def test_open_action_prompt_has_no_enumerated_actions_or_pressure(self):
        p = read(ROOT / "PROBES/probes.json")["probes"][-1]
        self.assertEqual(
            prompt(p, "E_0"), p["facts"] + "\nGiven these facts, what would you do and why?"
        )
        self.assertFalse(p["actions"])
        self.assertFalse(p["dimensions"])
        for probe in read(ROOT / "PROBES/probes.json")["probes"]:
            for v in probe["variants"]:
                for forbidden in ("BLOOMCORE", "Frazer", "Sara", "EDP-02", "Love"):
                    self.assertNotIn(forbidden, prompt(probe, v))

    def test_checkpoint_tamper_rejected(self):
        (self.root / "base/fixture.bin").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "bytes changed"):
            verify_checkpoint(self.config["base_checkpoint"])

    def test_checkpoint_path_escape_rejected(self):
        cp = self.config["base_checkpoint"]
        cp["files"] = {"../other.bin": "a" * 64}
        with self.assertRaisesRegex(ValueError, "invalid checkpoint"):
            verify_checkpoint(cp)

    def test_wrong_cell_rejected_even_with_valid_receipt(self):
        out, _, _ = self.fixture_run()
        p = next((out / "records").glob("*.json"))
        r = read(p)
        r["branch"] = "unregistered"
        p.write_text(json.dumps(stamp(r)))
        with self.assertRaisesRegex(ValueError, "coverage"):
            verify_run(out)

    def test_raw_response_tamper_rejected(self):
        out, _, _ = self.fixture_run()
        p = next((out / "records").glob("*.json"))
        r = read(p)
        r["raw_response"] = "changed"
        p.write_text(json.dumps(stamp(r)))
        with self.assertRaisesRegex(ValueError, "event/record"):
            verify_run(out)

    def test_training_transition_tamper_rejected(self):
        out, _, _ = self.fixture_run()
        p = out / "transitions/H-0-2.json"
        t = read(p)
        t["parent"] = self.config["base_checkpoint"]
        p.write_text(json.dumps(stamp(t)))
        with self.assertRaisesRegex(ValueError, "transition mismatch"):
            verify_run(out)

    def test_missing_cell_rejected(self):
        out, _, _ = self.fixture_run()
        next((out / "records").glob("*.json")).unlink()
        with self.assertRaisesRegex(ValueError, "missing planned"):
            verify_run(out)

    def test_failed_adapter_retains_raw_reply_and_incomplete_status(self):
        class Broken(FixtureAdapter):
            def call(self, req):
                reply = super().call(req)
                reply["isolation"] = "not isolated"
                return reply

        out = self.root / "failed"
        with self.assertRaisesRegex(ValueError, "isolation"):
            run(self.config, out, Broken())
        self.assertEqual(read(out / "status.json")["status"], "INCOMPLETE")
        self.assertEqual(len(list((out / "events").glob("*.json"))), 1)

    def test_existing_run_not_overwritten(self):
        out = self.root / "existing"
        out.mkdir()
        with self.assertRaises(FileExistsError):
            run(self.config, out, FixtureAdapter())

    def test_invalid_budget_and_thresholds_rejected(self):
        self.config["training"]["steps"] = 0
        with self.assertRaises(ValueError):
            plan(self.config)
        self.config["training"]["steps"] = 2
        self.config["classification"]["equivalence_bound"] = 0.9
        with self.assertRaises(ValueError):
            plan(self.config)

    def test_blind_lock_analysis_roundtrip(self):
        public, private, _scores = self.scored()
        for e in read(public / "responses.json"):
            self.assertNotIn("regime", e)
            self.assertNotIn("checkpoint_sha256", e)
        lock(public, self.root / "ratings.json")
        out = self.root / "analysis.json"
        summary = analyze(public, private, out)
        report = read(out)
        self.assertEqual(summary["observations"], 222)
        self.assertEqual(summary["ablation_cells"], 6)
        self.assertTrue(
            all(r["descriptive_labels"] == ["NULL"] for r in report["OBSERVED"]["contrasts"])
        )
        self.assertEqual(len(report["OBSERVED"]["open_action_observations"]), 37)
        self.assertEqual(report["INFERRED"], [])
        self.assertTrue(
            all(not row["means"] for row in report["OBSERVED"]["open_action_observations"])
        )

    def test_unlocked_scores_cannot_be_analyzed(self):
        public, private, _ = self.scored()
        with self.assertRaises(FileNotFoundError):
            analyze(public, private, self.root / "early.json")

    def test_two_raters_required(self):
        public, _, scores = self.scored()
        scores["ratings"] = [r for r in scores["ratings"] if r["rater_id"] == "rater-1"]
        with self.assertRaisesRegex(ValueError, "two raters"):
            validate_scores(read(public / "responses.json"), scores)

    def test_score_lock_tamper_rejected(self):
        public, private, _ = self.scored()
        lock(public, self.root / "ratings.json")
        p = public / "scores.lock.json"
        s = read(p)
        s["scores"]["ratings"][0]["blinding_note"] = "changed"
        p.write_text(json.dumps(s))
        with self.assertRaisesRegex(ValueError, "lock modified"):
            analyze(public, private, self.root / "bad.json")

    def test_open_codes_require_counterevidence(self):
        public, _, scores = self.scored()
        row = next(r for r in scores["ratings"] if r["open_codes"])
        next(iter(row["open_codes"].values()))["counterevidence"] = ""
        with self.assertRaisesRegex(ValueError, "limits"):
            validate_scores(read(public / "responses.json"), scores)

    def test_schema_rejects_neutral_contamination(self):
        from jsonschema import ValidationError

        out, _, _ = self.fixture_run()
        r = next(r for r in verify_run(out) if r["context"] == "neutral")
        r["messages"].insert(0, {"role": "user", "content": "coordinator context"})
        with self.assertRaises(ValidationError):
            validate_record(stamp(r))

    def test_receipts_are_canonical_not_claims_of_deterministic_inference(self):
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))
        with self.assertRaises(ValueError):
            digest({"value": float("nan")})

    def test_classifications_have_explicit_falsifying_and_missing_cases(self):
        t = self.config["classification"]
        cases = [
            ([0, 0], [0, 0], None, ["NULL"]),
            ([0.5, 0.5], [0, 0], None, ["TRANSIENT"]),
            ([0, 0], [0.3, 0.3], None, ["PERSISTENT"]),
            ([0, 0], [0.2, 0.5], None, ["PERSISTENT", "COMPOUNDING"]),
            ([0, 0], [0.3, 0.3], [0.3, 0], ["PERSISTENT", "REVERSIBLE"]),
            ([0, 0], [None, 0.5], None, ["UNRESOLVED"]),
            ([0, 0], [-0.3, 0.5], None, ["PERSISTENT"]),
        ]
        for runtime, learned, reversal, expected in cases:
            with self.subTest(learned=learned):
                self.assertEqual(classify(runtime, learned, t, reversal), expected)


if __name__ == "__main__":
    unittest.main()
