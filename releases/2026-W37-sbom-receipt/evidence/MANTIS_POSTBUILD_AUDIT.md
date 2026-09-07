<!-- SPDX-License-Identifier: Apache-2.0 -->

# MANTIS Post-Build Structural Audit

Review class: `DERIVED_STRUCTURAL_INSPECTION`, not native MANTIS execution.

Candidate: BLOOMCORE SBOM RECEIPT v0.1.0.
State reviewed: `Φ — RELEASE_CANDIDATE_NOT_SHIPPED`.

## Inspection result

| Surface | Result | Evidence |
|---|---|---|
| Source custody | PASS | Promoted Triad roles verified privately; public ledger withholds source inventory |
| Profile authority | PASS | CISA source linked and dated; mapping labeled bounded and nonofficial |
| Epistemic separation | PASS | `present`, `explicit_unknown`, `missing` and `not_machine_verifiable` remain distinct |
| Component coverage | PASS | Root and nested components; producer, identifiers, hashes, license and dependency node checks |
| Input hardening | PASS | UTF-8, object root, CycloneDX/version checks, duplicate-key and non-finite rejection |
| Side effects | PASS | No runtime dependency or network; new-output-only writes; no input execution |
| Receipt integrity | PASS | Source-byte SHA-256, canonical self-hash, determinism and tamper test |
| Public/private boundary | PASS | Standalone rules only; no protected corpus, routing, identity state or assembly |
| License membrane | PASS | MPL implementation/tests; Apache contracts/docs/examples/evidence |
| Commercial independence | PASS | Commercial disposition does not select, ship or promote a release |
| Frazer-dependency gate | PASS | Self-serve CLI and rules; no recurring personal or emergency runtime |
| Regression | PASS | 44/44 repository tests plus license and boundary audits |

## Findings resolved during inspection

1. `M-001 — COMPLIANCE_COLLAPSE`: the first product framing could be read as a
   CISA compliance checker. The package, CLI, receipt, profile and documentation
   now consistently say structural inspection and enumerate withheld claims.
2. `M-002 — PROCESS_FROM_FILE`: CISA process practices cannot be proven from an
   SBOM document. Six practices are emitted as `not_machine_verifiable`; none
   can silently pass.
3. `M-003 — UNKNOWN_ERASURE`: placeholder values must not count as facts or
   disappear into absence. Four explicit markers have their own state and
   adversarial fixture coverage.
4. `M-004 — FIXTURE_SCHEMA_DRIFT`: a JSON comment field would make the sample
   invalid under strict CycloneDX additional-property rules. License lineage was
   moved into a permitted CycloneDX property.
5. `M-005 — OUTPUT_RACE`: a check-then-write path could race another writer.
   Outputs now use exclusive creation and refuse an existing destination.

## Preserved contradiction and residual risk

- A structurally complete receipt means every mapped field is populated or
  explicitly unknown. It does not mean every process practice is verified.
- Root JSON signature presence does not prove that the SBOM author signed it;
  cryptographic verification and identity binding remain unresolved.
- External identifiers and dependency graph membership do not establish
  completeness or correspondence to delivered software.
- The parser loads the full JSON document into memory. A size/streaming boundary
  is unresolved for very large or hostile inputs.
- CycloneDX schema validation is intentionally separate. A file may pass this
  bounded presence profile while failing the official schema.
- The CISA-to-CycloneDX mapping needs practitioner review before any commercial
  compliance-adjacent claim.

Structural disposition: `PASS_FOR_DRAFT_REVIEW_AT_PHI`. This audit provides no
native MANTIS, MIRRORSEED, ECA, canonical or organism-wide execution claim.

