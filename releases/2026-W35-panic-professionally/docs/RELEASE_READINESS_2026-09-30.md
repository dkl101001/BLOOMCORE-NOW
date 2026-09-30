<!-- SPDX-License-Identifier: Apache-2.0 -->

# Maintenance Release Readiness - 2026-09-30

Status: `RELEASE_CANDIDATE_NOT_PUBLIC`

Panic Professionally v0.1.0 remains `1 - ACTIVE` under its original human
approval. This maintenance candidate fixes and packages existing behavior; it
is not a new release approval and does not authorize a tag, registry upload,
deployment or customer communication.

## Verified changes

- made CLI action-assignment output safe on restricted Windows console encodings;
- made the dashboard use a SQLite read-only connection and verified that reads
  do not create or change the selected database;
- included the dashboard command and HTML in the installable wheel;
- included full MPL-2.0 and AGPL-3.0-only texts and accurate multi-license
  package metadata;
- added a cross-platform, explicitly synthetic operational demo;
- narrowed receipt-chain claims to exclude undetectable trailing-suffix removal
  when no external chain-head anchor exists;
- preserved the original authorship, lineage, version and approval receipt.

## Fresh verification evidence

Environment: Windows, CPython 3.12.14. These are fresh maintenance-candidate
results, not the counts in the historical v0.1.0 release receipt.

| Check | Fresh result |
| --- | --- |
| Product tests | PASS - 9/9 |
| Repository regression tests | PASS - 99/99 across W31, W35, W36, EDP-01 and EDP-02 |
| Repository license audit | PASS - 184 text files inspected |
| Repository boundary audit | PASS |
| Python compilation | PASS for product packages, apps, tests and examples |
| Standard source install | PASS in a clean virtual environment with the declared build backend |
| Wheel build | PASS - `panic_professionally-0.1.0-py3-none-any.whl` |
| Offline wheel install | PASS in a second clean virtual environment |
| Installed CLI | PASS - lifecycle, action assignment, export and receipt verification |
| Installed dashboard | PASS - HTML and incident API; database SHA-256 unchanged by reads |
| Tamper handling | PASS - modified event reported invalid and `verify` exited 2 |
| Serious synthetic demo | PASS - 10-event valid chain plus Markdown and JSON exports |

The locally built review wheel was 33,033 bytes with SHA-256
`ee2eab9e1b3fab859a68b149345f0cd2635e40ae94182b57d7587278363ad402`.
Artifact hashes identify this local build only; no package registry upload was
performed.

## Reproduce

From `releases/2026-W35-panic-professionally`:

```bash
python3 -m unittest discover -s tests -v
python3 examples/serious_demo.py --output-dir /tmp/panic-professionally-demo
python3 -m pip wheel --no-deps --wheel-dir dist .
python3 -m venv /tmp/panic-professionally-venv
/tmp/panic-professionally-venv/bin/python -m pip install --no-index dist/panic_professionally-0.1.0-py3-none-any.whl
/tmp/panic-professionally-venv/bin/panic-professionally --help
/tmp/panic-professionally-venv/bin/panic-professionally-dashboard --help
```

From the repository root, after installing `EDP-01/requirements.txt`:

```bash
python3 forge_tools/run_all_tests.py
```

On Windows, preserve the frozen W36 fixture bytes as documented in the root
README before running the aggregate audit.

## Not established

- Python 3.11 or 3.13, macOS, and Linux installation were not freshly rerun in
  this local pass; CI is responsible for its configured Linux/Python matrix.
- No external security assessment, load test or multi-user threat model was run.
- No buyer demand, price, efficacy, incident-reduction or market-fit claim was
  tested.
- A valid receipt chain does not establish that recorded statements are true.

## Decisions still requiring a person

- whether and when to approve a new maintenance version and tag;
- package-registry and GitHub Release publication policy;
- pricing, support expectations and intended customer segment;
- whether external chain-head anchoring belongs in a future version;
- whether the dashboard should remain loopback-only or receive a separately
  reviewed authentication and deployment threat model.
