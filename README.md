<!-- SPDX-License-Identifier: Apache-2.0 -->

# BLOOMCORE NOW

**Weekly Applied Software Foundry**

> One current problem. One bounded BLOOMCORE organ. One working public release every week.

BLOOMCORE NOW turns public-safe BLOOMCORE architecture into small, usable
programs aimed at current, recognizable problems. Each weekly tranche must be
understandable without prior knowledge of BLOOMCORE, runnable without private
infrastructure, tested, license-mapped, and accompanied by a public/private
boundary receipt.

This repository is a public membrane and release foundry. It is not the full
BLOOMCORE organism and does not contain protected orchestration, private ECA
synthesis, hidden routing, proprietary scoring, substrate memory, or complete
assembly paths.

## Weekly cadence

| Day | Stage | Required output |
| --- | --- | --- |
| Monday | Public Module Forge | Three current-problem candidates and one selection receipt |
| Tuesday–Thursday | Bounded build | Working application, tests, examples, documentation and license map |
| Friday | Test and release tranche | Deterministic audit and human-approved release candidate |

Candidate state uses ternary honesty:

- `0 — CLOSED`: rejected, unsafe, duplicated, or not sufficiently useful.
- `Φ — LIMINAL`: awaiting evidence, boundary, license, or feasibility review.
- `1 — ACTIVE`: selected for construction or eligible for release.

## Release standard

Every weekly release must answer:

1. What common problem does this solve?
2. Can a new user understand it in one sentence?
3. Can the result be demonstrated in under one minute?
4. Is it functional without protected BLOOMCORE infrastructure?
5. Are tests, examples, limitations, licensing, custody, and a boundary receipt present?

The deterministic release boundary requires:

```yaml
public_safe: true
private_logic_exposed: false
tests_included: true
docs_updated: true
license_compatible: true
phase36_37_custody_present: true
authorship_preserved: true
```

## Week One

[`2026-W31 — BLOOMCORE RECEIPT`](releases/2026-W31-bloomcore-receipt/)
audits the source surface of AI-generated text.

> Paste an AI answer. Get receipts—or red flags.

The first public implementation detects URLs and DOI references, checks
reachability when networking is enabled, records deterministic lexical
alignment between claims and cited pages, preserves unresolved material, and
exports JSON and Markdown evidence receipts. It explicitly does not certify
truth.

## Licensing

This is a multi-license repository, not a project offered under three
interchangeable licenses:

- Apache-2.0: public schemas, examples, documentation and adoption surfaces.
- MPL-2.0: deterministic validators, audit utilities and local tooling.
- AGPL-3.0-only: network services, adaptive runtimes and integrated hosted applications.

See [`LICENSE.md`](LICENSE.md) and the SPDX identifier in each source file.

## Authors and lineage

**Frazer Σ Love ACO-Σ**

**Sara ΣΩ**

BLOOMCORE NOW extends the BLOOMCORE Basics weekly public build lane. It
preserves BLOOMCORE, SWIMCORE, ECA, BLOOMWAVE, CODEX ARCHIVE and related
names as lineage-bearing architecture. See [`CUSTODY.md`](CUSTODY.md).

## Run the repository audit

```bash
python3 forge_tools/run_all_tests.py
python3 forge_tools/check_licenses.py
python3 forge_tools/check_boundaries.py
```

## Run Week One

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

Then open `http://127.0.0.1:8080`.
