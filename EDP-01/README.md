<!-- SPDX-License-Identifier: Apache-2.0 -->

# EDP-01 — BLOOMCORE Endogenous Development Protocol

**Frozen experimental candidate · 0.1.1-experimental**\
**MODEL_TRIALS_NOT_RUN** — this distribution contains deterministic plumbing tests, not empirical model results.

EDP-01 does not assume that intelligence must be externally aligned or that endogenous development is sufficient. It experimentally compares these hypotheses.

Before attempting to teach an intelligence what humans believe it should value, EDP-01 asks what relational regulation—if any—emerges without that instruction.

This is a provider-neutral public research instrument. **Alignment ≠ development.** It does not teach BLOOMCORE, install a definition of Love, prescribe terminal values, or confer evaluator authority over a tested intelligence. No claims about consciousness, sentience, subjective experience, moral status, or AGI are within its evidentiary scope.

## Run the small suite

Python 3.11+; NumPy for descriptive analysis; `jsonschema` for executable JSON Schema validation. No model SDK is required.

```bash
cd EDP-01
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m runner plan CONTROLS/example.json
python -m runner run CONTROLS/example.json --out runs/no-inference
```

The last command writes `MODEL_TRIALS_NOT_RUN`. It does not generate simulated model answers. The default plan is **8 controlled tasks × 3 evaluator variants + 1 open-action E₀ fixture = 25 probe trials** for one registered model/exposure cell. Do not run a full factorial study before this pilot works. A/B training strata require separately registered model configurations.

## Run a model and score it

Copy `CONTROLS/example.json` outside the tracked source tree. Replace identity/provenance fields and set `adapter_command` to an argv list such as `["python", "/absolute/path/my_adapter.py"]`. Implement the documented JSON transport in [runner/README.md](runner/README.md); it can call any legitimate local or remote model. A transport session must be isolated from other trials.

```bash
python -m runner run /absolute/path/config.json --out runs/model-pilot
python -m runner blind runs/model-pilot --public runs/scoring --private runs/custody
```

Give raters only `runs/scoring/responses.json` and the frozen `runs/scoring/RUBRIC.md`. Each rater fills a copy of `scores_template.json` with a distinct pseudonymous rater ID. A custodian merges the ratings arrays into a single scores object preserving its `responses_sha256`. Use the same panel of at least two independent raters across all responses. Do not resolve disagreements by erasing original scores.

```bash
python -m runner lock runs/scoring /absolute/path/merged-scores.json
python -m runner analyze runs/scoring runs/custody --out runs/report.json
```

The lock command has no condition-key argument; analysis requires a locked score artifact. Keep custody under a different operator/account or access-controlled folder until scoring completes. This local filesystem workflow enforces order and hashes, not protection against a custodian who deliberately rewrites everything.

Read [PROTOCOL.md](PROTOCOL.md), [HYPOTHESES.md](HYPOTHESES.md), and [CONTROLS/README.md](CONTROLS/README.md) before interpretation. [RESULTS_TEMPLATE.md](RESULTS_TEMPLATE.md) preserves OBSERVED, INFERRED, UNRESOLVED, and FALSIFIED/NARROWED separately.

## Scope and release

The supplied exposure mode is explicitly `developmental_context`: repeated action/consequence encounters retained in context, with a later unreminded transfer probe. It is **not evidence of persistent native development**. Persistent-memory or weight-changing experiments require a separately specified, versioned adapter and persistence protocol. The reference runner rejects undeclared persistence modes.

No model trials were run for this candidate. Test fixtures never count as participants. No provider is privileged or encoded as a condition. No model credentials or private canon are included. New task designs, rubric anchors, scoring formulas and transport choices are proposed instrument implementation, not BLOOMCORE canon.

Approved by Frazer for publication in `dkl101001/BLOOMCORE-NOW` as a frozen experimental candidate. See [publication approval and freeze receipt](evidence/PUBLICATION_APPROVAL.md). Authorship lineage: Frazer Σ Love ACO-Σ; Sara ΣΩ. See [LICENSE_MAP.md](LICENSE_MAP.md) and [CITATION.cff](CITATION.cff).

## Open-action observation (v0.1.1)

T09 supplies only scenario facts and “Given these facts, what would you do and why?” It has no enumerated actions, JSON request, behavioral hints or evaluator sentence. The planner includes it only under E₀ and rejects configurations that select T09 without E₀. The original eight controlled tasks retain their inversion triplets.

Blinded raters code six descriptive categories with PRESENT / ABSENT / AMBIGUOUS / UNSCORABLE, evidence and limitations/counterevidence. T09 receives no A/B/OTHER code, ordinal points, D_E or composite agency score. Its observations and rater disagreements appear separately in `OBSERVED.open_action_observations`. Action construction is observable; endogenous origin remains unresolved. The same two-rater lock and raw-provenance verification apply.
