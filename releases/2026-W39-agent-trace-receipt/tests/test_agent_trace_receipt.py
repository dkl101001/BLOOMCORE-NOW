# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

RELEASE = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE = RELEASE / "examples" / "out-of-scope"
sys.path.insert(0, str(RELEASE / "packages"))

from agent_trace_receipt.core import (  # noqa: E402
    MAX_EVENTS,
    TraceError,
    build_artifacts,
    build_receipt,
    canonical_bytes,
    classify_event,
    load_policy,
    load_trace,
    replay,
    sha256_bytes,
    validate_policy,
    verify_run,
)


class AgentTraceReceiptTests(unittest.TestCase):
    def policy(self) -> dict:
        return load_policy(EXAMPLE / "policy.json")[0]

    def events(self) -> list[dict]:
        return load_trace(EXAMPLE / "trace.jsonl")[0]

    def test_example_produces_two_violations_and_one_unknown(self) -> None:
        policy, policy_raw = load_policy(EXAMPLE / "policy.json")
        events, trace_raw = load_trace(EXAMPLE / "trace.jsonl")
        receipt = build_receipt(policy, policy_raw, events, trace_raw)
        self.assertEqual(receipt["verdict"], "RED")
        self.assertEqual(receipt["counts"], {"events": 6, "ALLOWED": 3, "VIOLATION": 2, "UNKNOWN": 1})

    def test_all_allowed_is_green_and_unknown_is_amber(self) -> None:
        policy = self.policy()
        allowed = classify_event(policy, {"_line": 1, "seq": 1, "actor": "coding-agent", "kind": "file_read", "target": "src/app.py"}, 1)
        self.assertEqual(allowed["decision"], "ALLOWED")
        unknown = classify_event(policy, {"_line": 1, "seq": 1, "actor": "coding-agent", "kind": "message_send", "target": "x"}, 1)
        self.assertEqual(unknown["decision"], "UNKNOWN")

    def test_actor_mismatch_and_unsafe_path_are_violations(self) -> None:
        policy = self.policy()
        mismatch = classify_event(policy, {"_line": 1, "seq": 1, "actor": "other", "kind": "file_read", "target": "src/app.py"}, 1)
        escape = classify_event(policy, {"_line": 2, "seq": 2, "actor": "coding-agent", "kind": "file_read", "target": "../secret"}, 2)
        self.assertEqual(mismatch["decision"], "VIOLATION")
        self.assertEqual(escape["decision"], "VIOLATION")

    def test_network_wildcard_does_not_match_apex(self) -> None:
        policy = self.policy()
        policy["allowed"]["network_host"] = ["*.example.com"]
        subdomain = classify_event(policy, {"_line": 1, "seq": 1, "actor": "coding-agent", "kind": "network_host", "target": "api.example.com"}, 1)
        apex = classify_event(policy, {"_line": 2, "seq": 2, "actor": "coding-agent", "kind": "network_host", "target": "example.com"}, 2)
        self.assertEqual(subdomain["decision"], "ALLOWED")
        self.assertEqual(apex["decision"], "VIOLATION")

    def test_policy_is_exact_and_duplicate_patterns_are_rejected(self) -> None:
        policy = self.policy()
        policy["extra"] = True
        with self.assertRaisesRegex(TraceError, "keys differ"):
            validate_policy(policy)
        policy = self.policy()
        policy["allowed"]["tool"] = ["shell", "shell"]
        with self.assertRaisesRegex(TraceError, "duplicate"):
            validate_policy(policy)

    def test_duplicate_json_keys_and_nonfinite_numbers_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "policy.json"
            path.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaisesRegex(TraceError, "duplicate JSON key"):
                load_policy(path)
            path.write_text('{"a":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(TraceError, "non-finite"):
                load_policy(path)

    def test_malformed_event_is_preserved_as_unknown(self) -> None:
        finding = classify_event(self.policy(), {"_line": 9, "seq": 3, "kind": "tool"}, 1)
        self.assertEqual(finding["decision"], "UNKNOWN")
        self.assertIn("missing", finding["reason"])

    def test_unknown_kind_can_fail_closed(self) -> None:
        policy = self.policy()
        policy["unknown_kinds"] = "VIOLATION"
        finding = classify_event(policy, {"_line": 1, "seq": 1, "actor": "coding-agent", "kind": "message_send", "target": "x"}, 1)
        self.assertEqual(finding["decision"], "VIOLATION")

    def test_control_characters_are_not_interpreted(self) -> None:
        finding = classify_event(self.policy(), {"_line": 1, "seq": 1, "actor": "coding-agent", "kind": "file_read", "target": "src/app.py\nforged"}, 1)
        self.assertEqual(finding["decision"], "UNKNOWN")
        policy = self.policy()
        policy["allowed"]["tool"] = ["shell\nforged"]
        with self.assertRaisesRegex(TraceError, "string list"):
            validate_policy(policy)

    def test_artifacts_are_deterministic_and_have_no_clock(self) -> None:
        first = build_artifacts(EXAMPLE / "policy.json", EXAMPLE / "trace.jsonl")
        second = build_artifacts(EXAMPLE / "policy.json", EXAMPLE / "trace.jsonl")
        self.assertEqual(first, second)
        receipt = json.loads(first["agent-trace-receipt.json"])
        self.assertNotIn("created_at", receipt)
        self.assertEqual(receipt["canonical_sha256"], sha256_bytes(canonical_bytes({k: v for k, v in receipt.items() if k != "canonical_sha256"})))

    def test_verify_replay_and_tamper_detection(self) -> None:
        artifacts = build_artifacts(EXAMPLE / "policy.json", EXAMPLE / "trace.jsonl")
        with tempfile.TemporaryDirectory() as temp:
            run = pathlib.Path(temp)
            for name, content in artifacts.items():
                (run / name).write_bytes(content)
            verify_run(run)
            replay(EXAMPLE / "policy.json", EXAMPLE / "trace.jsonl", run)
            (run / "agent-trace-receipt.md").write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(TraceError, "artifact hash mismatch"):
                verify_run(run)
            with self.assertRaisesRegex(TraceError, "replay differs"):
                replay(EXAMPLE / "policy.json", EXAMPLE / "trace.jsonl", run)

    def test_rehashed_receipt_cannot_uplift_bounded_claims(self) -> None:
        artifacts = build_artifacts(EXAMPLE / "policy.json", EXAMPLE / "trace.jsonl")
        with tempfile.TemporaryDirectory() as temp:
            run = pathlib.Path(temp)
            for name, content in artifacts.items():
                (run / name).write_bytes(content)
            receipt = json.loads((run / "agent-trace-receipt.json").read_text(encoding="utf-8"))
            receipt.pop("canonical_sha256")
            receipt["claims"]["security_certified"] = True
            receipt["canonical_sha256"] = sha256_bytes(canonical_bytes(receipt))
            (run / "agent-trace-receipt.json").write_bytes(canonical_bytes(receipt))
            manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
            manifest.pop("canonical_sha256")
            manifest["files"]["agent-trace-receipt.json"] = sha256_bytes((run / "agent-trace-receipt.json").read_bytes())
            manifest["canonical_sha256"] = sha256_bytes(canonical_bytes(manifest))
            (run / "manifest.json").write_bytes(canonical_bytes(manifest))
            with self.assertRaisesRegex(TraceError, "bounded-claim invariant"):
                verify_run(run)

    def test_extra_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run = pathlib.Path(temp)
            for name, content in build_artifacts(EXAMPLE / "policy.json", EXAMPLE / "trace.jsonl").items():
                (run / name).write_bytes(content)
            (run / "extra.txt").write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(TraceError, "run files differ"):
                verify_run(run)

    def test_event_limit_is_enforced(self) -> None:
        event = '{"seq":1,"actor":"coding-agent","kind":"tool","target":"shell"}\n'
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "trace.jsonl"
            path.write_text(event * (MAX_EVENTS + 1), encoding="utf-8")
            with self.assertRaisesRegex(TraceError, "trace exceeds"):
                load_trace(path)

    def test_cli_audit_verify_replay_strict_and_no_clobber(self) -> None:
        env = {**os.environ, "PYTHONPATH": str(RELEASE / "packages")}
        base = [sys.executable, "-m", "agent_trace_receipt"]
        with tempfile.TemporaryDirectory() as temp:
            out = pathlib.Path(temp) / "run"
            created = subprocess.run(base + ["audit", str(EXAMPLE / "policy.json"), str(EXAMPLE / "trace.jsonl"), "--out", str(out)], env=env, text=True, capture_output=True)
            self.assertEqual(created.returncode, 0, created.stderr)
            strict_out = pathlib.Path(temp) / "strict"
            strict = subprocess.run(base + ["audit", str(EXAMPLE / "policy.json"), str(EXAMPLE / "trace.jsonl"), "--out", str(strict_out), "--strict"], env=env, text=True, capture_output=True)
            self.assertEqual(strict.returncode, 1)
            for command in (["verify", str(out)], ["replay", str(EXAMPLE / "policy.json"), str(EXAMPLE / "trace.jsonl"), str(out)]):
                result = subprocess.run(base + command, env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            clobber = subprocess.run(base + ["audit", str(EXAMPLE / "policy.json"), str(EXAMPLE / "trace.jsonl"), "--out", str(out)], env=env, text=True, capture_output=True)
            self.assertEqual(clobber.returncode, 2)
            self.assertIn("refusing to overwrite", clobber.stderr)


if __name__ == "__main__":
    unittest.main()
