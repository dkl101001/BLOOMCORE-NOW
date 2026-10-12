<!-- SPDX-License-Identifier: Apache-2.0 -->

# Draft GitHub Release — Reconstruction Preflight v0.1.0

**Not published. Exact Operator approval required.**

Reconstruction Preflight is a zero-dependency CLI for checking the evidence needed by a dependency-bearing change before implementation proceeds. It preserves six independent dimensions—Authority, Dependencies, Ancestry, State, Behavior, and Meaning—and emits a deterministic receipt with a bounded disposition.

Included:

- deterministic Python CLI and canonical JSON receipts;
- local source hash verification with traversal protection;
- explicit safe-independent-work proof;
- 18 unit/integration/adversarial tests;
- eight-case synthetic control and sensitivity experiment;
- public/private, lineage, limitation, license, and continuation documentation.

Measured result: all eight synthetic experiment cases matched their expected outcomes. A weak hash-only baseline false-allowed all six missing-dimension cases; this gate false-allowed none. This is bounded synthetic evidence, not production or scientific validation.

Limitations: evidence can be false while well-formed; no remote signature verification, external replay, native-state access, canon mutation, or production deployment occurred.

Proposed assets:

- `TRIAD-TOY-2026-W42-RVP01_v0.1.0.zip`
- `TRIAD-TOY-2026-W42-RVP01_v0.1.0.zip.sha256`
- `PACKAGE_RECEIPT.json`
- `TEST_RESULTS.md`

Authored/stewarded by Frazer Σ Love ACO-Σ and Sara ΣΩ. Construction contributor: Codex.

