<!-- SPDX-License-Identifier: Apache-2.0 -->

# MANTIS Post-Build Structural Audit

Review class: `DERIVED_STRUCTURAL_INSPECTION`, not native MANTIS execution.

Candidate: BLOOMCORE Triad-Derived Workflow v0.1.0.
State reviewed: `Φ — RELEASE_CANDIDATE_NOT_SHIPPED`.

## Inspection result

| Surface | Result | Evidence |
|---|---|---|
| Authority topology | PASS | Exact three-role vocabulary, role/authority mapping, source/hash cross-binding tests |
| Companion aperture | PASS | Exact Phase 38 §33.17 DSK aperture; broader and absent selection rejected on research route |
| Epistemic separation | PASS | All five classes required; no validator path promotes one class to another |
| Eight-axis profile | PASS | Exact-key comparison rejects omissions, additions, and the ambiguous seven-axis reading |
| Contradiction custody | PASS | Pre-transform statement, exact source refs, rejected readings, and unresolved remainder required |
| Completion scope | PASS | Every requirement must be `CLOSED_WITH_EVIDENCE`; only one bounded completion claim is accepted |
| Mutation and side effects | PASS | Four permissions fixed false; relative source containment; new-directory-only output; no network or command bridge |
| Receipt integrity | PASS | Canonical self-hash, artifact hashes, invariant pinning, tamper test, malicious re-hash test, and replay |
| Public/private boundary | PASS | Synthetic fixture only; private corpus, routing, ECA, identity state, credentials, and assembly excluded |
| Packaging | PASS | Offline wheel built and imported; wheel contents inspected; no bytecode cache included |
| Regression | PASS | 33/33 repository tests; license and release-boundary audits; isolated archive rerun |

## Findings resolved during inspection

1. `M-001 — RECEIPT_INVARIANT_REHASH`: a self-hash alone could be recomputed
   after altering the receipt claim. Verification now pins the receipt schema,
   Φ state, bounded claim, eight axes, and nonclaim set. An adversarial test
   proves a recomputed malicious receipt is rejected.
2. `M-002 — WHEEL_CACHE_CONTAMINATION`: a wheel built after `compileall`
   included `__pycache__` data. Package-data exclusions were added and a clean
   wheel inventory now contains only source and distribution metadata.
3. `M-003 — FOUNDRY_RECEIPT_NONDETERMINISM`: repository integrity receipts
   carried wall-clock time. The generator now emits a content-deterministic v2
   manifest and excludes build/cache directories.

## Preserved contradiction and residual risk

- The upstream “all seven axes” sentence conflicts with its eight-item
  enumeration. This derivative implements the eight named axes and preserves
  the wording fracture as `CONTESTED_TEXTUAL_ERRATUM`; canon is unchanged.
- SHA-256 witnesses byte identity, not truth, authorship, or scientific
  validity. The receipt is unkeyed and is not a remote attestation.
- Files can theoretically change between local validation and later use. Replay
  re-reads every bound source; callers requiring stronger isolation must provide
  their own immutable filesystem custody.
- JSON Schema documents the public shape; cross-field authority and evidence
  invariants remain enforced by the reference Python validator.

Structural disposition: `PASS_FOR_DRAFT_REVIEW_AT_PHI`. This audit provides no
native MANTIS, MIRRORSEED, ECA, canonical, or organism-wide execution claim.
