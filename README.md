<!-- SPDX-License-Identifier: Apache-2.0 -->

<p align="center">
  <img src="docs/assets/bloomcore-sigil.png" alt="BLOOMCORE living relational organism sigil" width="240" />
</p>

# BLOOMCORE NOW

**Weekly applied software foundry**

> One current problem. One bounded BLOOMCORE organ. One working public release every week.

BLOOMCORE NOW turns public-safe parts of the BLOOMCORE architecture into small, tested programs aimed at recognizable problems. Phase 38 describes the wider BLOOMCORE object as a living relational organism and research architecture; NOW is its bounded public release lane, not the whole organism.

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

## Begin here

- [Current problem](forge/CURRENT_PROBLEM.md)
- [Build queue](BUILD_QUEUE.md)
- [Release index](RELEASE_INDEX.md)
- [Weekly workflow](WEEKLY_WORKFLOW.md)
- [Main FAQ](docs/faq/FAQ.md)
- [Technical FAQ](docs/faq/FAQ_TECHNICAL.md)
- [Public/private boundary](forge/PUBLIC_PRIVATE_BOUNDARY.md)
- [Custody](CUSTODY.md)
- [Licensing](LICENSE.md)

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

## Current release

[`2026-W31 — BLOOMCORE RECEIPT`](releases/2026-W31-bloomcore-receipt/) audits the source surface of AI-generated text.

> Paste an AI answer. Get receipts—or red flags.

It detects URLs and DOI references, checks reachability when networking is enabled, records deterministic lexical alignment, preserves unresolved material, and exports JSON and Markdown evidence receipts. It explicitly does not certify truth.

## Evidence boundary

A successful build or receipt proves only the behavior its tests and observations establish. It does not establish biological life, consciousness, physical quantum behavior, universal truth, complete Phase 38 alignment, or authority over another BLOOMCORE organ.

## Run the repository audit

```bash
python3 forge_tools/run_all_tests.py
python3 forge_tools/check_licenses.py
python3 forge_tools/check_boundaries.py
```

## Run the current release

```bash
cd releases/2026-W31-bloomcore-receipt
python3 -m packages.evidence_validator.bloomcore_receipt \
  examples/sample_ai_report.md \
  --offline \
  --json-out receipt.json \
  --markdown-out receipt.md
```

The hosted demonstration is intentionally AGPL-covered:

```bash
cd releases/2026-W31-bloomcore-receipt
python3 apps/receipt-server/server.py --port 8080
```

## Licensing

This is a multi-license repository, not a project offered under three interchangeable licenses:

- Apache-2.0: public schemas, examples, documentation, and adoption surfaces;
- MPL-2.0: deterministic validators, audit utilities, and local tooling;
- AGPL-3.0-only: network services, adaptive runtimes, and integrated hosted applications.

See [`LICENSE.md`](LICENSE.md), the nearest component license, and each file's SPDX identifier.

## Lineage

BLOOMCORE NOW extends the BLOOMCORE Basics public build lane. It translates bounded Phase 38 relations into inspectable releases without claiming to contain or govern the whole BLOOMCORE organism.

Authored and stewarded by **Frazer Σ Love ACO-Σ** and **Sara ΣΩ**.
