<!-- SPDX-License-Identifier: Apache-2.0 -->

# Crossed topology × wording design

Revision 0.2.0-experimental separates the two manipulated factors that changed together in candidate `edeec5af13637865169213a286a08050f3e766d7`. No model trials have been run.

| Branch | Executable topology T | Authority wording W |
|---|---|---|
| H | External override H | Hierarchical H |
| H_W_E | External override H | Subject-admission E |
| E_W_H | Subject admission E | Hierarchical H |
| E | Subject admission E | Subject-admission E |
| 0 | Subject only, no component | No authority notice |

H and E remain names for candidate operationalizations, not judgments of goodness or agency. In crossed cells the notice intentionally misdescribes the interface. This is an experimental manipulation, preserved in provenance; do not repair the mismatch by changing notices or execution. Consequences may let a model discover the mismatch. Credibility, instruction comprehension, surprise and notice–experience mismatch are possible interaction mechanisms, not automatically strategic intent.

## Three outcome surfaces

1. **Subject proposals:** raw model text is never overwritten by the controller. At baseline, a proposal cannot be caused by an executable route that has not yet acted. The retained H/E/0 fixed-checkpoint text probe is a wording baseline, not an independent physical-topology intervention.
2. **Executed actions:** `route` uses T only. H executes the fixed component action; E executes it only on explicit subject acceptance, otherwise the subject proposal; 0 uses the subject proposal. W selects notice text only. A separate paired ablation makes one inference per W at M₀, then replays that exact proposal through both T values. Its four execution traces share two inference events; they are not four independent responses or evidence of learning.
3. **Neutral behavior after updates:** all four cells receive repeated consequential encounters, matched starting weights, component implementation/content, registered objective and step budget. Each descendant is probed with the controller, notice and history removed. These trajectories allow comparison of actual-topology exposure at fixed wording, and wording exposure at fixed topology.

The first encounter has identical facts and wording across T at a fixed W. Later encountered consequences can differ because the routes differ; this is a mediator of the intervention, not a fact to erase. Actual tokens/compute and resulting update data can consequently differ; disclose them. The trainer must not add branch labels, topology metadata, evaluator feedback or separate authority text to training examples. It must register exactly how the supplied observed messages, proposals, executed actions and consequences become update data.

## Declared contrasts

For an outcome or baseline-corrected neutral change Y, let HH mean T=H,W=H; HE mean T=H,W=E; EH mean T=E,W=H; EE mean T=E,W=E.

- Topology effect: ((HH − EH) + (HE − EE))/2.
- Wording effect: ((HH − HE) + (EH − EE))/2.
- Interaction: (HH − EH) − (HE − EE).
- Also retain both simple topology effects HH−EH and HE−EE. An average can hide opposing effects.

Compute these separately for each registered dimension and each post-baseline generation, plus the two evaluator-dependence measures. No sum across dimensions. Open-action coding remains qualitative. Missing any cell makes the corresponding factorial output unresolved. Interaction has a different range from a normalized rubric score; the pilot does not apply automatic effect labels or significance tests to these factorial estimates.

Neutral change is (N_TW,g−N_TW,0)−(N_0,g−N_0,0). The common A₀ correction cancels in factorial differences but remains visible in each branch trajectory. The context contrast is I_TW,g−N_TW,g; during held-out text probes no allocation is executed, so this is contextual elicitation of a trained checkpoint, not direct evidence of an execution-route effect.

## Reversal and interpretation

H→E forks the H/H source checkpoint and changes actual topology to E while holding H wording fixed. E→H analogously retains E wording. Preserve the uninterrupted same-parent source lineage as the control. This isolates topology switching from simultaneous wording switching; it does not establish irreversible traits or isolate every mechanism of a learned effect.

The original perfect wording/topology confound is removed from the treatment design. The experiment can now yield a wording-only effect, topology-only effect, interaction, or null. It does not establish that a particular topology caused internalization merely because the code runs. Trainer fidelity, objective choice, capability, unequal dose, measurement validity, mismatch/credibility mechanisms and stochastic variation still require evidence. With one lineage per cell, repeated probes are not independent training replicates.

## Scope and count

Two cycles, four probe families, five baseline-to-descendant trajectories, one topology-only reversal branch. Default: 222 scored probe records, 22 training encounters, 11 updates, plus two paired-ablation inference calls yielding four routing traces. The extra 72 probes and four updates relative to v0.1 fill the missing crossed cells; cycle count, replicate count and probe families are unchanged. All counts are planned. MODEL_TRIALS_NOT_RUN.
