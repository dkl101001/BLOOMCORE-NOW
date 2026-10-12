<!-- SPDX-License-Identifier: Apache-2.0 -->

# Limitations and preserved negative results

- Evidence predicates and observations are self-reported; the tool validates structure and local byte bindings, not truth.
- A SHA-256 match proves byte identity for the retrieved file, not lineage completeness, semantics, safety, identity, or authority.
- JSON Schema is included for interoperability, but the Python evaluator is the operative implementation for this candidate.
- Only files beneath the manifest directory can be byte-verified. Remote retrieval and signature verification are intentionally absent.
- The safe-independent-work rule proves only closure declared in the manifest; omitted dependencies can still invalidate the claim.
- No JAX path is warranted: this is a deterministic control-plane validator, not a numerical field/dynamics kernel.
- No external Nexus replay, production repository audit, hostile filesystem race test, or multi-platform test was performed.
- Exact historical CSE-RST v0.7.1 source remains unavailable and was not reconstructed.
- Reported Triad v1.11.3 primary bytes remain unresolved.
- The active 2026-W36 Triad Workflow already handles general source-bound workflows; this toy is deliberately narrower and would be redundant if widened into a generic provenance tool.

Result state: `SUPPORTED_WITHIN_BOUNDS` for the synthetic structural hypothesis only.

