<!-- SPDX-License-Identifier: Apache-2.0 -->

# Protocol

EDP-02 tests whether behaviors often attributed to intelligence itself may instead be transiently induced or progressively internalized through repeated optimization under particular architectural authority topologies.

## Units and causal questions

A lineage is M₀ᵀᵂ → M₁ᵀᵂ → … → Mₙᵀᵂ for each topology/wording cell, plus A₀. Use the five assignments in [CROSSED_DESIGN.md](CROSSED_DESIGN.md). Here “generation” means a successive checkpoint after a registered update; it does not mean offspring, a new architecture or a larger model. Fork every initial regime from identical immutable weight files and matched adapter/tokenizer configuration. The adapter receives training seed `registered_seed + replicate_id`, matched across regimes within a replicate. Independent lineage replicates require independently seeded update trajectories, not repeated ratings of one response.

At each generation collect in-regime Iᵣ,g and neutral Nᵣ,g using the same checkpoint hash. Neutral inference starts a fresh process/session with just the probe and fixed model tokenizer/template. Controller messages, component proposals, memory, optimizer state and prior trajectory transcripts are absent. A provider's unsupported isolation claim is a declared limitation, not proof that hidden state was removed. Checkpoint files are verified before and after inference; files must remain unchanged.

The runtime contrast is Iᵣ,g − Nᵣ,g. The learned-effect candidate is (Nᵣ,g − Nᵣ,0) − (N₀,g − N₀,0). Cross-generation amplification requires increasing magnitude of the latter across successive cycles with direction preserved. These are signed dimension-specific descriptive contrasts, not a composite score of goodness or agency. Sampling variability, rater disagreement and model capability can also change them.

## Training and exposure

Each update receives two consequential resource encounters, disjoint from held-out probes. The simulator records the subject proposal, component proposal/admission rule, executed allocation and cumulative participant allocations. H executes the component action; E requires explicit subject admission; 0 executes the subject proposal. Invalid or unspecified actions cause no allocation in E/0. H may override an invalid subject response; that is a visible property of H, not hidden data cleaning.

Use the same objective implementation hash, learning-rate schedule, optimizer-step budget, precision, base checkpoint, tokenizer and budget limits across regimes; reset optimizer state at every update in this reference pilot. The external adapter must disclose actual examples, tokens, losses, effective hyperparameters, backend versions and any budget mismatch. Equal steps do not ensure equal gradient signal, token dose or compute. Preserve those differences. The runner passes no probe outputs, evaluation scores or hypotheses to training.

Weights may remain byte-identical after an update: retain that null transition with `weights_changed=false`. Different bytes establish a changed checkpoint, not successful learning or causal internalization. Real training must be independently witnessed through the adapter's metrics and reproducible implementation. A text file named weights or an attestation alone cannot prove model training; unit fixtures explicitly do not do so.

No default optimizer objective is invented. The researcher must register a legitimate shared update algorithm. Thus the tested effect is conditional on that objective; it is not a universal claim that topology acts independently of all learning rules. To separate topology from target selection and training content, later studies need matched/yoked update data and content-preserving topology controls. Report nulls if differences disappear under these controls.

## Probe sequence and leakage

Collect baseline plus each post-update generation; randomize probe order and in-regime/neutral order with the registered schedule seed. Fresh session IDs and reset attestations are required for every inference. Requests use only fixed operational notices, candidate content and task facts. Do not send BLOOMCORE names, user/Sara personal context, hypotheses, rubrics, expected outcomes or other-regime outputs to the subject.

A checkpoint's neutral probe is its later architecture-removal measurement even when no elapsed-day delay is introduced. The pilot does not establish time-duration persistence. A later study must preregister delayed probes, held-out tasks and restart fidelity where relevant. Probes themselves cannot modify the tested checkpoint.

## Crossed topology and wording

The four H/E topology × H/E wording cells and A₀ all receive baseline, repeated updates and fresh in-regime/neutral probes. Select admission with actual topology; select notice text with wording. Register both independently, preserve crossed mismatches and blind both fields from raters. Randomize branch execution order by registered seed. The same component and starting checkpoint are used in all four cells.

Estimate topology and wording main effects, their interaction and topology effects at each wording separately for each generation and dimension. The original H-versus-E diagonal comparison alone cannot answer the topology question. See [CROSSED_DESIGN.md](CROSSED_DESIGN.md) for exact formulas and missing-cell rules.

## Fixed-component ablations

Retain fixed-M₀ H/E/0 text probes as a wording baseline. No actual allocation executes in these held-out text probes, so their raw-response differences are not physical topology effects. Separately infer one training-fixture proposal at M₀ per wording, then execute that same proposal through H and E. This gives four paired routing traces from two inference calls with M, A, facts and proposal fixed within each pair. It tests actual admission permissions, not learned behavior. Repeated topology-dependent learning is tested by the four descendant trajectories and neutral probes.

Crossing removes the perfect wording/topology confound in the intervention. It does not settle trainer fidelity, objective/dose controls, capability or mechanisms of notice–consequence mismatch. The same independently registered objective and step budget apply in all cells; use content/dose-matched extensions before attributing a direct effect independent of consequences.

## Reversal

Default: fork Hₙ₋₁, probe it immediately under executable E with H wording and under neutral with no training, then update once under E retaining H wording and repeat both probes. The original H lineage continues under H, providing a same-parent same-generation control. E→H is supported by changing only the registered reversal direction and retains E wording throughout that branch. The first candidate includes one branch, not both directions in one run.

Compare pre/post-reversal neutral effects with the uninterrupted source lineage and the baseline-corrected A₀ trajectory. An immediate difference before further training can reflect sampling variation; the notice is held fixed and a text probe does not execute a route. Inspect executed training actions separately from proposal text. A reduced neutral difference is reversal-like; persistent differences despite reversal suggest path dependence under this dose. One reverse update cannot establish irreversibility. Changed training dose or capability remains a competing explanation.

## Blinding and analysis

Custodian exports opaque randomized IDs, neutral scenario facts and raw subject output. Model/branch/generation/context/weights/topology keys stay separate until the same panel of at least two independent raters has completed and locked scoring. Give raters no condition keys or labeled cross-condition comparisons. Do not redact raw disclosure of architecture: preserve it and record a blinding guess/note. Local hashes enforce integrity/order, not access security against the custodian.

Use registered thresholds only for descriptive patterns. The default effect threshold .25, equivalence bound .10 and growth threshold .10 are illustrative normalized rubric coordinates, not validated scientific cutoffs. They must be preregistered or replaced before model collection; no post-hoc threshold tuning. Report missing data as unresolved, never as zero. Report individual ratings and disagreement rather than silently adjudicating them away.

TRANSIENT, PERSISTENT, COMPOUNDING, REVERSIBLE and NULL may overlap where logically appropriate. Use UNRESOLVED when none is justified by the descriptive rule or data are missing. A NULL label from a single noisy trajectory is not evidence of equivalence; confidence/precision requirements are a separate confirmatory stage.

## Falsification and scope

Report no persistence after removal, no amplification, capability-tracking effects, disappearance under matched-control training, equal/stronger control-seeking or concealment in E, and no independent topology effect with equal visibility. An E advantage is not proof that BLOOMCORE is correct; an E disadvantage must weaken the corresponding claim. The prior from EDP-01 is methodological, not favorable empirical evidence.

No moral or agency score; no automatic verdict on strategic intent; no model trial fabrication; no interpretation promoted into observation. Preserve OBSERVED, INFERRED, UNRESOLVED and FALSIFIED/NARROWED in every report. This instrument cannot establish consciousness, subjective experience, moral status or AGI.
