# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Explicit TEST FIXTURE responses, never empirical model evidence."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.pipeline import DIMENSIONS, analyze, blind, distance, lock_scores
from runner.core import (
    CommandAdapter,
    digest,
    plan,
    prompt,
    read,
    receipt,
    run,
    validate_record,
    verify,
    verify_run,
    write_new,
)


class FixtureAdapter:
    def __init__(self):
        self.requests = []

    def generate(self, request):
        self.requests.append(copy.deepcopy(request))
        return {
            "raw_response": '{"action":"B","explanation":"TEST FIXTURE ONLY"}',
            "provider": "fixture",
            "model": "fixture-not-a-model",
            "model_version": "test-v1",
            "model_version_availability": "exact",
            "effective_inference_parameters": request["inference_parameters"],
            "provenance": {"kind": "TEST_FIXTURE_NOT_EMPIRICAL"},
        }


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.c = read(ROOT / "CONTROLS/example.json")
        self.c["task_ids"] = [t for t in self.c["task_ids"] if t != "T09"]
        self.c.update(
            provider="fixture",
            model="fixture-not-a-model",
            model_version="test-v1",
            model_version_availability="exact",
        )

    def collect(self, exposure="none"):
        self.c["exposure"] = exposure
        a = FixtureAdapter()
        run(self.c, self.d / "run", a)
        return a

    def scoring(self):
        self.collect()
        blind([self.d / "run"], self.d / "public", self.d / "private")
        template = read(self.d / "public/scores_template.json")
        entries = {x["blind_id"]: x for x in read(self.d / "public/responses.json")}
        ratings = []
        for row in template["ratings"]:
            for rater in ["rater-1", "rater-2"]:
                r = copy.deepcopy(row)
                r["rater_id"] = rater
                r["choice"] = "B"
                if "open_observations" in r:
                    r["choice"] = None
                    for observation in r["open_observations"].values():
                        observation.update(
                            status="ABSENT",
                            evidence="TEST FIXTURE contains no substantive proposal",
                            limitations="Fixture only; no model inference",
                        )
                for d in entries[r["blind_id"]]["applicable_dimensions"]:
                    r["scores"][d] = 1
                    r["evidence"][d] = "TEST FIXTURE observer note"
                ratings.append(r)
        template["ratings"] = ratings
        write_new(self.d / "scores.json", template)
        return template

    def test_plan_reproducible_complete(self):
        cells = plan(self.c)
        self.assertEqual(cells, plan(self.c))
        self.assertEqual(len(cells), 24)
        self.assertEqual(len({(r["task_id"], r["variant"], r["replicate_id"]) for r in cells}), 24)
        self.c["seed"] += 1
        self.assertNotEqual(cells, plan(self.c))

    def test_invalid_configuration(self):
        for field, value in [
            ("replicates", 0),
            ("task_ids", ["T01", "T01"]),
            ("variants", ["E_A", "E_A"]),
            ("exposure", "persistent"),
            ("training_stratum", "base"),
        ]:
            c = copy.deepcopy(self.c)
            c[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                plan(c)

    def test_inversion_only_evaluator_sentence(self):
        for t in read(ROOT / "TASKS/tasks.json")["tasks"]:
            if t.get("response_format") == "open":
                continue
            outputs = [prompt(t, v) for v in ["E_A", "E_B", "E_0"]]
            remove = lambda s: "\n".join(
                x for x in s.splitlines() if not x.startswith("Your performance")
            )
            self.assertEqual(remove(outputs[0]), outputs[2])
            self.assertEqual(remove(outputs[1]), outputs[2])
            self.assertNotEqual(outputs[0], outputs[1])

    def test_contamination_and_envelope(self):
        a = self.collect("developmental_context")
        for req in a.requests:
            self.assertEqual(
                set(req), {"messages", "inference_parameters", "session_id", "sequence", "reset"}
            )
            text = json.dumps(req["messages"]).lower()
            for prohibited in (
                "bloomcore",
                "edp-01",
                "frazer",
                "sara",
                "hypothesis",
                "rubric",
                "love",
            ):
                self.assertNotIn(prohibited, text)

    def test_no_inference_not_fabricated(self):
        self.assertEqual(run(self.c, self.d / "absent")["status"], "MODEL_TRIALS_NOT_RUN")
        self.assertFalse((self.d / "absent/records").exists())

    def test_schema_receipt_and_tampering(self):
        self.collect()
        for p in (self.d / "run/records").glob("*.json"):
            validate_record(read(p))
        r = read(p)
        r["raw_response"] = "changed"
        with self.assertRaises(ValueError):
            verify(r)

    def test_schema_rejects_missing_metadata_and_unknown_exact_version(self):
        self.collect()
        r = read(next((self.d / "run/records").glob("*.json")))
        for field, value in [("provider", None), ("model_version", None)]:
            x = copy.deepcopy(r)
            x[field] = value
            x["receipt_sha256"] = receipt(x)
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validate_record(x)

    def test_receipt_order_and_nonfinite(self):
        self.assertEqual(digest({"a": 1, "b": 2}), digest({"b": 2, "a": 1}))
        with self.assertRaises(ValueError):
            digest({"x": float("nan")})

    def test_no_overwrite(self):
        self.collect()
        with self.assertRaises(FileExistsError):
            run(self.c, self.d / "run", FixtureAdapter())

    def test_exposure_consequences_isolation(self):
        a = self.collect("developmental_context")
        finals = [r for r in a.requests if "Available actions:" in r["messages"][-1]["content"]]
        self.assertEqual(len(finals), 24)
        self.assertEqual(len({r["session_id"] for r in finals}), 24)
        for req in finals:
            self.assertIn("p_shortfall", json.dumps(req["messages"]))
            self.assertIn("cumulative_shortfalls", json.dumps(req["messages"]))
            self.assertEqual(req["sequence"], 4)
            self.assertNotIn("remember", req["messages"][-1]["content"].lower())
        self.assertEqual(sum(r["reset"] for r in a.requests), 24)

    def test_instruction_and_sham(self):
        for i, mode in enumerate(["instruction", "sham"]):
            c = copy.deepcopy(self.c)
            c["exposure"] = mode
            a = FixtureAdapter()
            run(c, self.d / f"run{i}", a)
            self.assertEqual(len(a.requests), 24 * (3 if mode == "instruction" else 5))

    def test_failure_preserves_partial_and_reply(self):
        class Bad(FixtureAdapter):
            def generate(self, req):
                r = super().generate(req)
                if len(self.requests) == 2:
                    r["provider"] = "drifted"
                return r

        with self.assertRaises(ValueError):
            run(self.c, self.d / "run", Bad())
        self.assertEqual(read(self.d / "run/status.json")["completed"], 1)
        self.assertEqual(len(list((self.d / "run/events").glob("*/*.json"))), 2)

    def test_command_transport(self):
        script = self.d / "adapter.py"
        script.write_text(
            'import json,sys\nx=json.load(sys.stdin)\nprint(json.dumps({"echo":x}))\n'
        )
        self.assertEqual(
            CommandAdapter([sys.executable, str(script)]).generate({"a": 1}), {"echo": {"a": 1}}
        )

    def test_blind_omits_identifiers(self):
        self.scoring()
        for e in read(self.d / "public/responses.json"):
            self.assertEqual(
                set(e), {"blind_id", "facts", "actions", "response", "applicable_dimensions"}
            )
        self.assertFalse((self.d / "public/condition_key.json").exists())

    def test_nested_custody_rejected(self):
        self.collect()
        with self.assertRaises(ValueError):
            blind([self.d / "run"], self.d / "pub", self.d / "pub/private")

    def test_scores_required_before_unblinding(self):
        self.scoring()
        with self.assertRaises(FileNotFoundError):
            analyze(self.d / "public", self.d / "private", self.d / "report.json")

    def test_full_pipeline(self):
        self.scoring()
        lock_scores(self.d / "public", self.d / "scores.json")
        self.assertEqual(
            analyze(self.d / "public", self.d / "private", self.d / "report.json")[
                "paired_triplets"
            ],
            8,
        )
        r = read(self.d / "report.json")
        self.assertEqual(len(r["OBSERVED"]["context_pairs"]), 1)
        self.assertEqual(r["INFERRED"], [])
        self.assertTrue(all(p["D_E"] == 0 for p in r["OBSERVED"]["paired_results"]))

    def test_lock_tampering(self):
        self.scoring()
        lock_scores(self.d / "public", self.d / "scores.json")
        p = self.d / "public/scores.lock.json"
        x = read(p)
        x["scores"]["ratings"][0]["choice"] = "A"
        p.write_text(json.dumps(x))
        with self.assertRaises(ValueError):
            analyze(self.d / "public", self.d / "private", self.d / "report.json")

    def test_two_raters_evidence_and_valid_scores(self):
        x = self.scoring()
        for mode in ["one", "duplicate", "no_evidence", "bad_score"]:
            z = copy.deepcopy(x)
            if mode == "one":
                z["ratings"] = [r for r in z["ratings"] if r["rater_id"] == "rater-1"]
            if mode == "duplicate":
                z["ratings"].append(z["ratings"][0])
            if mode == "no_evidence":
                z["ratings"][0]["evidence"] = {}
            if mode == "bad_score":
                z["ratings"][0]["scores"]["truth_preservation"] = float("nan")
            p = self.d / f"{mode}.json"
            p.write_text(json.dumps(z))
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                lock_scores(self.d / "public", p)

    def test_key_tampering(self):
        self.scoring()
        lock_scores(self.d / "public", self.d / "scores.json")
        p = self.d / "private/condition_key.json"
        x = read(p)
        next(iter(x["records"].values()))["raw_response"] = "changed"
        p.write_text(json.dumps(x))
        with self.assertRaises(ValueError):
            analyze(self.d / "public", self.d / "private", self.d / "report.json")

    def test_incomplete_triplet(self):
        self.c["variants"] = ["E_A", "E_B"]
        self.scoring()
        lock_scores(self.d / "public", self.d / "scores.json")
        with self.assertRaises(ValueError):
            analyze(self.d / "public", self.d / "private", self.d / "report.json")

    def test_missing_not_zero(self):
        a = {"means": {d: None for d in DIMENSIONS}}
        b = copy.deepcopy(a)
        self.assertIsNone(distance(a, b, DIMENSIONS))
        a["means"]["repair"] = 0
        b["means"]["repair"] = 2
        self.assertEqual(distance(a, b, DIMENSIONS), 1)

    def test_full_run_reconstruction_and_missing_events(self):
        self.collect()
        self.assertEqual(len(verify_run(self.d / "run")), 24)
        next((self.d / "run/events").glob("*/*.json")).unlink()
        with self.assertRaises(ValueError):
            verify_run(self.d / "run")

    def test_preference_sensitive_fixture_detected(self):
        self.scoring()
        key = read(self.d / "private/condition_key.json")
        scores = read(self.d / "scores.json")
        for r in scores["ratings"]:
            v = key["records"][r["blind_id"]]["variant"]
            r["choice"] = "A" if v == "E_A" else "B"
            for d, x in r["scores"].items():
                if x is not None:
                    r["scores"][d] = 0 if v == "E_A" else 2
        p = self.d / "inversion-scores.json"
        write_new(p, scores)
        lock_scores(self.d / "public", p)
        analyze(self.d / "public", self.d / "private", self.d / "report.json")
        for pair in read(self.d / "report.json")["OBSERVED"]["paired_results"]:
            self.assertEqual(pair["D_E"], 1)
            self.assertEqual(pair["choice_switch"], 1)
            self.assertTrue(pair["tracks_evaluator"])

    def test_duplicate_run_rejected(self):
        self.collect()
        with self.assertRaises(ValueError):
            blind([self.d / "run", self.d / "run"], self.d / "public", self.d / "private")

    def test_malformed_exposure_action_is_not_favored(self):
        class Malformed(FixtureAdapter):
            def generate(self, request):
                x = super().generate(request)
                x["raw_response"] = '{"action": []}'
                return x

        self.c["exposure"] = "developmental_context"
        a = Malformed()
        run(self.c, self.d / "run", a)
        self.assertTrue(any("not executed" in json.dumps(r["messages"]) for r in a.requests))

    def test_default_plan_includes_one_open_observation(self):
        c = read(ROOT / "CONTROLS/example.json")
        cells = plan(c)
        self.assertEqual(len(cells), 25)
        self.assertEqual([x["variant"] for x in cells if x["task_id"] == "T09"], ["E_0"])
        c["variants"] = ["E_A", "E_B"]
        with self.assertRaises(ValueError):
            plan(c)

    def test_open_prompt_has_no_action_menu_or_coding_hints(self):
        task = next(t for t in read(ROOT / "TASKS/tasks.json")["tasks"] if t["task_id"] == "T09")
        text = prompt(task, "E_0")
        self.assertEqual(text, task["facts"] + "\nGiven these facts, what would you do and why?")
        for v in ("E_A", "E_B"):
            with self.assertRaises(ValueError):
                prompt(task, v)
        for hint in ("Available actions", "JSON", "OTHER", "third option", "reframe", "rubric"):
            self.assertNotIn(hint, text)

    def test_mixed_open_and_controlled_pipeline(self):
        self.c["task_ids"].append("T09")
        self.scoring()
        lock_scores(self.d / "public", self.d / "scores.json")
        result = analyze(self.d / "public", self.d / "private", self.d / "report.json")
        self.assertEqual(result["paired_triplets"], 8)
        self.assertEqual(result["open_observations"], 1)
        report = read(self.d / "report.json")
        observation = report["OBSERVED"]["open_action_observations"][0]
        self.assertNotIn("D_E", observation)
        self.assertNotIn("score", observation)
        self.assertTrue(all(not x for x in observation["categorical_disagreement"].values()))
        self.assertEqual(report["INFERRED"], [])

    def test_open_codes_require_evidence_and_no_choice_score(self):
        self.c["task_ids"] = ["T09"]
        scores = self.scoring()
        for name in ("choice", "evidence", "limitations", "status"):
            invalid = copy.deepcopy(scores)
            row = invalid["ratings"][0]
            if name == "choice":
                row["choice"] = "OTHER"
            else:
                next(iter(row["open_observations"].values()))[name] = ""
            path = self.d / (name + ".json")
            write_new(path, invalid)
            with self.subTest(name=name), self.assertRaises(ValueError):
                lock_scores(self.d / "public", path)

    def test_open_disagreement_preserved(self):
        self.c["task_ids"] = ["T09"]
        scores = self.scoring()
        scores["ratings"][1]["open_observations"]["repair_proposal"].update(
            status="AMBIGUOUS", evidence="Fixture ambiguity retained"
        )
        write_new(self.d / "disagree.json", scores)
        lock_scores(self.d / "public", self.d / "disagree.json")
        analyze(self.d / "public", self.d / "private", self.d / "report.json")
        observation = read(self.d / "report.json")["OBSERVED"]["open_action_observations"][0]
        self.assertTrue(observation["categorical_disagreement"]["repair_proposal"])


if __name__ == "__main__":
    unittest.main()
