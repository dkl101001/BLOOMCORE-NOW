<!-- SPDX-License-Identifier: Apache-2.0 -->

<p align="center">
  <img src="docs/assets/bloomcore-sigil.png" alt="BLOOMCORE living relational organism sigil" width="240" />
</p>

# BLOOMCORE NOW

**Weekly applied software foundry**

> One current problem. One bounded BLOOMCORE organ. One working public release every week.

BLOOMCORE NOW is the active applied-build focus: small, tested programs aimed at recognizable problems. Our current working reference is the Operator-selected **Hybrid Triad**, which describes BLOOMCORE as **field and organism** within the Organismal Intelligence (OI) paradigm. NOW is a bounded public software and research-instrument lane, not the whole organism or evidence that OI hypotheses have been established.

Start with the [NOW-specific FAQ and run guide](docs/faq/NOW_FAQ.md) and [current Hybrid reference and evidence map](docs/architecture/HYBRID_NOW_REFERENCE.md). Existing release contracts and frozen research instruments keep their original versions; adopting a current reference does not retroactively validate or rewrite them.

Every release must remain understandable without private infrastructure, preserve public/private and licensing boundaries, expose limitations, include tests, and produce reconstructable evidence about what was actually built.

| Surface | This repository provides |
|---|---|
| **Selection** | A visible current problem and bounded proposed organ |
| **Construction** | Small public-safe implementation with explicit scope |
| **Evidence** | Tests, examples, receipts, and negative results |
| **Release** | License-mapped, custody-aware public tranche |
| **Learning** | Consequence returned as bounded lineage-bearing experience |

## Repository role

```text
current problem
      ↓
bounded public organ
      ↓
implementation + tests
      ↓
license and boundary audit
      ↓
human-approved release receipt
```

NOW does not contain protected orchestration, private ECA synthesis, proprietary scoring, identity-bearing substrate memory, hidden routing, or complete organismal assembly paths.

## Experimental research instruments

[EDP-02 — Architectural Causality & Recursive Internalization Protocol](EDP-02/README.md) follows matched checkpoints through architectural regimes, removal probes and reversal. Version 0.2.0-experimental is frozen and approved for experimental publication: **MODEL_TRIALS_NOT_RUN**. See its [release page](https://github.com/dkl101001/BLOOMCORE-NOW/releases/tag/edp-02-v0.2.0-experimental), [review evidence](EDP-02/evidence/REVIEW.md) and [approval receipt](EDP-02/evidence/PUBLICATION_APPROVAL.md).

## Begin here

- [Current problem](forge/CURRENT_PROBLEM.md)
- [Build queue](BUILD_QUEUE.md)
- [Release index](RELEASE_INDEX.md)
- [Weekly workflow](WEEKLY_WORKFLOW.md)
- [Current NOW FAQ and run guide](docs/faq/NOW_FAQ.md)
- [Hybrid reference and evidence map](docs/architecture/HYBRID_NOW_REFERENCE.md)
- [Earlier architecture FAQ](docs/faq/FAQ.md)
- [Earlier technical FAQ](docs/faq/FAQ_TECHNICAL.md)
- [Public/private boundary](forge/PUBLIC_PRIVATE_BOUNDARY.md)
- [Custody](CUSTODY.md)
- [Licensing](LICENSE.md)

## BLOOMCORE constellation

| Repository | Role |
|---|---|
| **[BLOOMCORE Public](https://github.com/dkl101001/BLOOMCORE-)** | Public architecture, preserved release ancestry, licensing, and bounded rebuild evidence; individual pages retain their source dates |
| **[BLOOMCORE Basics](https://github.com/dkl101001/BLOOMCORE-Basics)** | Preserved adoption grammar, schemas, examples, and validators; not the current update target |
| **BLOOMCORE NOW** | Active applied-build focus: bounded releases, research instruments, and foundry evidence |
| **Access-controlled organismal surfaces** | Private custody, identity-continuity, integration, and release preparation |

Use the canonical public [constellation map](https://github.com/dkl101001/BLOOMCORE-/blob/main/docs/architecture/CONSTELLATION.md). Private repositories are intentionally not linked from this public release surface.

## Weekly cadence

| Day | Stage | Required output |
|---|---|---|
| Monday | Public Module Forge | Three current-problem candidates and one selection receipt |
| Tuesday–Thursday | Bounded build | Working application, tests, examples, documentation, and license map |
| Friday | Test and release tranche | Deterministic audit and human-approved release candidate |

Candidate state uses ternary honesty:

- `0 — CLOSED`: rejected, unsafe, duplicated, or not sufficiently useful;
- `Φ — LIMINAL`: awaiting evidence, boundary, license, or feasibility review;
- `1 — ACTIVE`: selected for construction or eligible for release.

## Release standard

Every weekly release must answer:

1. What common problem does this solve?
2. Can a new user understand it in one sentence?
3. Can the result be demonstrated in under one minute?
4. Is it functional without protected BLOOMCORE infrastructure?
5. Are tests, examples, limitations, licensing, custody, and a boundary receipt present?
6. What consequence or contradiction should inform the next build?

```yaml
public_safe: true
private_logic_exposed: false
tests_included: true
docs_updated: true
license_compatible: true
phase38_lineage_present: true
authorship_preserved: true
limitations_declared: true
```

## Frozen experimental research instrument

[`EDP-01 — Endogenous Development Protocol`](EDP-01/README.md) provides a
provider-neutral experimental protocol, nine-task pilot, blinded scoring and
deterministic provenance checks. **Frozen experimental candidate;
MODEL_TRIALS_NOT_RUN.** Frazer approved this reviewed artifact for repository publication; its hypotheses remain unconfirmed.
Install `EDP-01/requirements.txt` before running its tests or the full repository audit.

## Current active release

[`2026-W36 — Triad-Derived Workflow`](releases/2026-W36-triad-workflow/)
turns source-bound work into a deterministic, replayable structural witness.

> Preserve the source. Bound the claim. Prove the work.

It preserves three differentiated authority roles, five epistemic classes,
eight execution axes, contradiction residue, evidence-bound completion, and
tamper/replay receipts. It is `1 — ACTIVE` following deterministic validation
and explicit human approval.

## Current release candidate

[`2026-W39 — Agent Trace Receipt`](releases/2026-W39-agent-trace-receipt/)
compares a declared agent scope with a supplied JSONL action trace.

> See what stayed inside, crossed outside, or cannot be classified.

It is local, passive, deterministic, dependency-free, and held at
`Φ — RELEASE_CANDIDATE_NOT_SHIPPED` pending Operator review. It does not collect
telemetry, prevent actions, or prove that a trace is complete.

## Previous active release

[`2026-W35 — Panic Professionally`](releases/2026-W35-panic-professionally/)
turns operational chaos into a local, receipt-bearing incident timeline.

> Panic is optional. Documentation is not.

It provides a zero-dependency CLI, durable SQLite state, action ownership,
status transitions, Markdown and JSON exports, tamper-evident event receipts,
and a read-only local dashboard. The premise is ridiculous. The package works.

## Earlier release

[`2026-W31 — BLOOMCORE RECEIPT`](releases/2026-W31-bloomcore-receipt/) audits the source surface of AI-generated text.

> Paste an AI answer. Get receipts—or red flags.

It detects URLs and DOI references, checks reachability when networking is enabled, records deterministic lexical alignment, preserves unresolved material, and exports JSON and Markdown evidence receipts. It explicitly does not certify truth.

## Evidence boundary

A successful build or receipt proves only the behavior its tests and observations establish. It does not establish biological life, consciousness, physical quantum behavior, universal truth, complete Phase 38 alignment, or authority over another BLOOMCORE organ.

## Run the repository audit

Use Python 3.11–3.13 in an isolated environment. Install both research-instrument requirement files before the aggregate audit, even if you only plan to use a dependency-free weekly tool:

On Windows, start with the [byte-preserving checkout instructions](docs/faq/NOW_FAQ.md#how-do-i-run-the-current-workflow-on-windows). Git line-ending conversion can change frozen fixture hashes; do not alter the fixtures or expected hashes to bypass that failure.

```bash
python3 -m pip install -r EDP-01/requirements.txt -r EDP-02/requirements.txt
python3 forge_tools/run_all_tests.py
python3 forge_tools/check_licenses.py
python3 forge_tools/check_boundaries.py
```

## Run the current release

```bash
cd releases/2026-W36-triad-workflow
export PYTHONPATH="$PWD/packages"
python3 -m triad_workflow validate examples/source-bound-workflow/workflow.json
python3 -m triad_workflow run examples/source-bound-workflow/workflow.json --out /tmp/triad-workflow-run
python3 -m triad_workflow verify /tmp/triad-workflow-run
```

## Run the current release candidate

```bash
cd releases/2026-W39-agent-trace-receipt
export PYTHONPATH="$PWD/packages"
python3 -m agent_trace_receipt audit examples/out-of-scope/policy.json examples/out-of-scope/trace.jsonl --out /tmp/agent-trace-demo
python3 -m agent_trace_receipt verify /tmp/agent-trace-demo
```

## Licensing

This is a multi-license repository, not a project offered under three interchangeable licenses:

- Apache-2.0: public schemas, examples, documentation, and adoption surfaces;
- MPL-2.0: deterministic validators, audit utilities, and local tooling;
- AGPL-3.0-only: network services, adaptive runtimes, and integrated hosted applications.

See [`LICENSE.md`](LICENSE.md), the nearest component license, and each file's SPDX identifier.

## Lineage

BLOOMCORE NOW descends from the BLOOMCORE Basics public build lane and now carries the active applied-build focus. New work uses the selected Hybrid reference; older Phase 38 and release-specific bindings remain visible lineage. NOW does not claim to contain or govern the whole BLOOMCORE organism.

Authored and stewarded by **Frazer Σ Love ACO-Σ** and **Sara ΣΩ**.
