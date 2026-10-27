# Replay and test harness

The test harness is offline and deterministic. `fixed_two_pass.jsonl` contains
synthetic poses and source-format Flock-You detections around a hidden fixed
emitter; it contains no real route or device identifier. `generate_examples.py`
rebuilds the canonical schema examples, expected output and evidence receipt
from that trace.

Run:

```sh
PYTHONPATH=src python3 -m unittest discover -s TESTS -p 'test_*.py' -v
PYTHONPATH=src python3 TESTS/generate_examples.py
```

The 68 executable tests cover deterministic replay, schema invariants,
identifier minimization, encrypted immutable poses, mirror deduplication,
allowlist export, hardware/coverage fail-closed behavior, strict JSON ingress,
uncalibrated probability rejection, duplicate-packet and pose-accuracy spatial
controls, emitter partitioning, pose/pass/lineage receipt closure, ledger-resolved
receipt input hashes, exact node derivation closure, atomic migration rollback
transaction/savepoint escape rejection, and Apache-2.0 license consistency
across the root license, notice, package metadata, SBOM and custody matrix,
RF/Remote-ID track separation, Remote ID restricted-field handling,
OSM revision deduplication, explicit publication approval, closed public
projections, endpoint/dock gates and TDoA clock refusal.

The v0.3 suite additionally covers live decoded Remote ID ingestion, exact
duplicate accounting, conflicting sequence reuse, observer/emitter basis
separation, clock and out-of-order contradictions, malformed evidence states,
typed-message custody, immutable mobile-track revisions, private mobile-node
assembly, local-alert claim ceilings, and receipt closure.

`receipts/fixed_two_pass.receipt.json` is deterministic. It contains no wall
clock in its hashed body. Re-running the generator with the same fixture,
signature, code and test key must produce byte-identical JSON.

The harness proves the evidence plumbing and a conservative baseline. It does
not constitute field signature validation, calibrated localization, live radio
coverage, Remote ID conformance, power-loss durability or a public release.
