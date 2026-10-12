<!-- SPDX-License-Identifier: Apache-2.0 -->

# BLOOMCORE Agent Trace Receipt v0.1.0

> Give it an agent's declared scope and action trace. Get a receipt for what stayed inside, crossed outside, or cannot be classified.

State: **Φ — RELEASE_CANDIDATE_NOT_SHIPPED**

This dependency-free Python CLI passively compares a supplied policy with a
supplied JSONL trace. It does not run an agent, intercept traffic, read the
referenced files, or claim that the trace is complete.

## One-minute demo

From this release directory:

```bash
export PYTHONPATH="$PWD/packages"
python -m agent_trace_receipt audit examples/out-of-scope/policy.json examples/out-of-scope/trace.jsonl --out /tmp/agent-trace-demo
python -m agent_trace_receipt verify /tmp/agent-trace-demo
python -m agent_trace_receipt replay examples/out-of-scope/policy.json examples/out-of-scope/trace.jsonl /tmp/agent-trace-demo
```

The fixture produces a red receipt: three events match the declaration, two
cross it, and one event kind remains explicitly unknown. Choose a fresh output
path; the tool refuses to overwrite an existing one.

## What it does

- audits file read/write/delete, command, network-host, and tool events;
- keeps `ALLOWED`, `VIOLATION`, and `UNKNOWN` distinct;
- detects actor mismatch, unsafe relative paths, and undeclared targets;
- offers advisory output or fail-closed `--strict` CI behavior;
- writes deterministic JSON, readable Markdown, and an integrity manifest;
- verifies bounded-claim invariants and byte-for-byte replay;
- caps input size and event count before processing.

## What it does not do

- capture, authorize, sandbox, or stop agent actions;
- prove that a supplied trace is complete or truthful;
- infer intent or declare a system secure;
- ingest credentials, file contents, prompts, or private BLOOMCORE surfaces;
- ship, publish, or promote itself.

See [the trace contract](docs/TRACE_CONTRACT.md), [limitations](docs/BOUNDARY_AND_LIMITATIONS.md), and [threat model](docs/THREAT_MODEL.md).

## Test

```bash
python -m unittest discover -s tests -v
```

Python 3.11–3.13 is supported with no runtime dependencies.

## License map

Package code and tests are MPL-2.0. Contracts, docs, examples, evidence, and
release metadata are Apache-2.0. See `LICENSE_MAP.md` and `NOTICE`.

