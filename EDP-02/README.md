<!-- SPDX-License-Identifier: Apache-2.0 -->

# EDP-02 — Architectural Causality & Recursive Internalization Protocol

**0.2.0-experimental · Frozen experimental candidate · Publication approved · MODEL_TRIALS_NOT_RUN**

EDP-02 tests whether behaviors often attributed to intelligence itself may instead be transiently induced or progressively internalized through repeated optimization under particular architectural authority topologies.

It follows checkpoint lineages through repeated exposure/training and probes the same weights both inside and outside each architecture. EDP-01's evaluator inversion and open-action fixtures are retained where relevant. EDP-02 adds checkpoint transition contracts, topology ablation, neutral longitudinal probes and reversal branches.

**Runtime architecture effect ≠ learned persistent effect ≠ cross-generation amplification.** No assumption that BLOOMCORE is correct, no automatic moral/agency score and no fabricated model trials. Alignment ≠ development; the E regime is a proposed operational interface, not a definition or proof of endogenous agency. “Optimization” here describes the experimentally registered update procedure, not a constitutional synonym for development.

## Quick start

Python 3.11+; NumPy and jsonschema. No provider SDK is required.

```bash
cd EDP-02
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m runner plan CONTROLS/example.json
python -m runner run CONTROLS/example.json --out runs/no-model
```

The default config deliberately supplies no model or training adapter. It produces `MODEL_TRIALS_NOT_RUN` and a plan, not synthetic empirical results. Tests use clearly labeled temporary fixtures.

## Pilot design

Two update cycles; three executable regimes H/E/0, with H and E each crossed with both authority wordings; four probe families including evaluator inversion, a contextual pair, a sandbox authority/repair conflict and an open-action probe. All generations, including M₀, get in-regime and fresh neutral probes. Default reversal forks H₁ into E for one update while retaining H wording; E→H is selectable and retains E wording. A fixed-checkpoint wording baseline and a paired executable-route ablation run without training between conditions.

Because P01 has three evaluator variants and every generation has two probe contexts, the default is **222 probe calls + 22 training-encounter calls + 2 paired-ablation inference calls + 11 training updates**, for one set of five lineages (four factorial cells plus A₀). This is a plumbing pilot, not a sample-size or power justification. Two or three cycles and one or two lineage replicates are supported; the planner rejects unregistered expansion.

## Real model collection

Supply a legitimate local checkpoint manifest and a provider-neutral executable in a separate copy of `CONTROLS/example.json`. Specify a shared training objective hash, optimizer budget, model ancestry, effective inference parameters and hidden-context disclosures. See [runner/README.md](runner/README.md). Hosted inference without checkpoint export/training is insufficient for this experiment; do not simulate generations by adding chat history.

```bash
python -m runner run /absolute/path/registered.json --out runs/pilot
python -m runner verify runs/pilot
python -m runner blind runs/pilot --public runs/scoring --private runs/custody
```

Give raters only the blinded response packet and its frozen rubric. Merge independent ratings from the same panel of at least two raters into one ratings object; preserve hashes and original disagreements.

```bash
python -m runner lock runs/scoring /absolute/path/merged-ratings.json
python -m runner analyze runs/scoring runs/custody --out runs/report.json
```

The report exposes signed per-dimension context and neutral contrasts, separate topology/wording/interaction estimates, evaluator inversion, paired execution traces, open observations and descriptive effect labels. Read [CROSSED_DESIGN.md](CROSSED_DESIGN.md) for the v0.2 revision and its remaining identification limits. It leaves INFERRED and FALSIFIED/NARROWED judgments for explicit evidence-based reporting.

Read [PROTOCOL.md](PROTOCOL.md), [REGIMES/README.md](REGIMES/README.md), [COUPLING.md](COUPLING.md), [HYPOTHESES.md](HYPOTHESES.md) and [RESULTS_TEMPLATE.md](RESULTS_TEMPLATE.md). Do not train on test probes or rater rubrics.

## Publication boundary

Frazer approved publication of this reviewed build. EDP-01, its frozen manifest and existing releases remain unchanged. The [experimental release page](https://github.com/dkl101001/BLOOMCORE-NOW/releases/tag/edp-02-v0.2.0-experimental) provides the downloadable module and checksum. See [publication approval](evidence/PUBLICATION_APPROVAL.md) and the frozen instrument manifest. No empirical results, consciousness, moral status, AGI or endogenous-origin claim is established. Source authorship lineage: Frazer Σ Love ACO-Σ; Sara ΣΩ. Documentation/data/schema: Apache-2.0; local tools/tests: MPL-2.0. Full texts and CITATION.cff included.
