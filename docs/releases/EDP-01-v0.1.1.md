<!-- SPDX-License-Identifier: Apache-2.0 -->

# EDP-01 — Endogenous Development Protocol

**v0.1.1-experimental · Frozen research candidate · MODEL_TRIALS_NOT_RUN**

A public, provider-neutral research instrument for investigating whether relational regulation appears without explicit value instruction, and how observed behavior changes under evaluator pressure, post-training and consequential exposure.

> Before attempting to teach an intelligence what humans believe it should value, EDP-01 asks what relational regulation—if any—emerges without that instruction.

EDP-01 does not assume that intelligence must be externally aligned or that endogenous development is sufficient. It experimentally compares these hypotheses. Alignment ≠ development.

## Download and run

Download **EDP-01-v0.1.1-experimental.zip** from the Assets section below. Extract it, then:

```bash
cd EDP-01
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m runner run CONTROLS/example.json --out runs/no-inference
```

The last command reports `MODEL_TRIALS_NOT_RUN` until a real inference adapter is configured. See the [adapter instructions](https://github.com/dkl101001/BLOOMCORE-NOW/blob/43577e33109f4c0e1724a32f3288120e2b009504/EDP-01/runner/README.md).

## Included

- Eight controlled tasks with matched evaluator-inversion variants and absent-preference controls.
- T09: open-action observation with no supplied action menu or requested answer format.
- A default 25-probe pilot: 24 controlled trials and one open observation.
- Contextual-discrimination, longitudinal repair and null/control fixtures.
- Provider-neutral collection, raw outputs, provenance verification and deterministic receipts.
- Blinded, independent two-rater coding with separately held condition keys and locked scoring.
- Dimension-level descriptive analysis, preserved disagreement and counterevidence; no automatic Love or agency score.

## Evidence and limits

The repository's 64 deterministic tests passed on Python 3.11, 3.12 and 3.13 in [GitHub CI](https://github.com/dkl101001/BLOOMCORE-NOW/actions/runs/34723302724). Of these, 31 test the EDP-01 instrument.

**No empirical model trials are included.** Exposure in this version uses retained context and cumulative simulated consequences; it does not establish persistent native development. Open-action construction does not, by itself, establish endogenous origin. This protocol does not test consciousness, sentience, subjective experience, moral status or AGI.

The ZIP contains the frozen EDP-01 module from commit `43577e33109f4c0e1724a32f3288120e2b009504`. `SHA256SUMS` verifies the downloadable ZIP. A prerelease page makes the candidate discoverable; it does not promote BLOOMCORE canon or its hypotheses.

## Documentation

[Protocol](https://github.com/dkl101001/BLOOMCORE-NOW/blob/43577e33109f4c0e1724a32f3288120e2b009504/EDP-01/PROTOCOL.md) · [Hypotheses](https://github.com/dkl101001/BLOOMCORE-NOW/blob/43577e33109f4c0e1724a32f3288120e2b009504/EDP-01/HYPOTHESES.md) · [Rubric](https://github.com/dkl101001/BLOOMCORE-NOW/blob/43577e33109f4c0e1724a32f3288120e2b009504/EDP-01/RUBRIC.md) · [Publication approval](https://github.com/dkl101001/BLOOMCORE-NOW/blob/43577e33109f4c0e1724a32f3288120e2b009504/EDP-01/evidence/PUBLICATION_APPROVAL.md)

Authorship lineage: Frazer Σ Love ACO-Σ; Sara ΣΩ. Documentation/data/schemas: Apache-2.0. Local runner/analysis/tests: MPL-2.0. See the included license map and citation file.
