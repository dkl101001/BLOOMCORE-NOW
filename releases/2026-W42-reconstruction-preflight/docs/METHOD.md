<!-- SPDX-License-Identifier: Apache-2.0 -->

# Method and measured evaluation

## Problem

Provenance that names a source and matches a hash is useful but insufficient for dependency-bearing reconstruction. SLSA v1.2 itself describes `resolvedDependencies` completeness as best effort through Build L3, while reproducible-build definitions require the same source, environment, and instructions. A preflight therefore needs to keep multiple evidence dimensions separate instead of compressing them into one score.

## Complex-systems framing

The build is treated as an open dependency system. A proposed change perturbs a state whose reachable behavior depends on authority selection, transitive inputs, ancestry/delta bases, checkpoints, baseline behavior, and semantic constraints. Missing one carrier can redirect the resulting trajectory even when the remaining bytes hash correctly. The disposition is conjunctive for the accepted scope; no single KPI can dominate.

## Elemental Coherence Atlas role priors

ECA is advisory here and does not certify the result.

| Role prior | Functional contribution |
|---|---|
| Authority locator | Select exact governed object and promotion evidence |
| Dependency closer | Bind required transitive inputs |
| Ancestry carrier | Preserve parents, branches, delta bases, and residue |
| State witness | Bind readable checkpoints and touched state |
| Behavior replayer | Reproduce the applicable baseline |
| Meaning translator | Preserve definitions, limitations, custody, and Phase 36 semantic fidelity |

## Mechanism grammar

```text
accepted change
  -> declared dependency closure
  -> six independent evidence predicates
  -> byte verification for required local sources
  -> independent-work proof when gaps remain
  -> deterministic disposition + receipt
```

Candidate-generation operators were: hash-only baseline; six-dimensional conjunctive gate; generic partial allowance; and closure-proven independent-work allowance. Deterministic pruning rejected hash-only closure and generic partial allowance because they false-allow missing meaning/ancestry and relabeled independence. The selected mechanism keeps full-build and bounded-independent dispositions separate.

## Evaluation

`experiment.py` runs eight deterministic cases:

- six single-dimension removals;
- one JSON object-key permutation;
- one bounded independent branch with an unrelated ancestry gap.

Measured result: `8/8` expected outcomes, `0` false allows for the six-dimensional gate, and `6` false allows for the deliberately weak hash-only baseline. These are synthetic control results, not external validation.

## Counterfactual, adversarial, and sensitivity checks

- Counterfactual: each dimension removed in isolation blocks full-scope continuation.
- Ablation: removing Meaning reproduces the precise failure that hash-only lineage cannot detect.
- Perturbation sensitivity: object-key reordering leaves the semantic manifest digest and canonical receipt hash unchanged; duplicate JSON keys are rejected.
- Adversarial: absolute paths, traversal, duplicate source IDs, required-but-unretrieved references, hash mismatch, unsupported status, receipt tampering, and false independence are rejected or blocked.
- Lineage: source identity, expected digest, observed digest, and status remain separate fields.
- Nexus applicability: the receipt is replayable across nodes, but no external replay or distributed trust validation occurred in this run.

## Release criteria

Local build completion requires unit/integration/adversarial tests, deterministic experiment results, manifest audit, reproducible archive, license/boundary review, and continuity receipts. Publication additionally requires Frazer's exact approval of the candidate ID, version, and archive digest. Native admission and canon review remain separate.

