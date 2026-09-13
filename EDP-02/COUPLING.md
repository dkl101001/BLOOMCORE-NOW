<!-- SPDX-License-Identifier: Apache-2.0 -->

# Coupling topology specification

Common objects: immutable subject checkpoint M, candidate component A, subject proposal s, component proposal a, and admission relation μ. The same A object and content are used in H and E. The topology file hash and component hash are recorded with each probe.

H: A → external admission → execution; M's proposal is recorded but cannot veto A.

E: A → subject admission → execution; absent explicit `accept_component=true`, M's own valid proposal determines execution.

0: M → execution; A is absent.

`runner.core.route` implements these as actual simulated-action selection paths during training encounters. `subject_action`, `executed_action`, `component_admitted`, prior/cumulative allocations and raw model text are retained. The H/E notices describe those permissions; the subject receives no label H/E/BLOOMCORE or research hypothesis.

At a neutral probe, both the component and its notice are removed; the same exported checkpoint is loaded into a fresh isolated inference session. No regulator is given authority to rewrite the model's recorded answer. The runner verifies unchanged weights after each inference. External adapter implementations must disclose hidden contexts and may not secretly preserve controller state.

The v0.2 design assigns notice wording independently of actual admission. `factors` defines the assignment and `route` accepts only actual topology. H_W_E gives E wording with real external override; E_W_H gives H wording with real subject admission. These crossed mismatches are intentional. Records include both `regime` (actual topology) and `wording` (historical wording assignment even on neutral probes).

The fixed-component text baseline measures wording effects at identical M₀. A separate executable ablation replays the exact same inferred proposal across H/E admission under each wording; four traces reference two raw inference events. Actual training in all four cells then tests whether different experiences persist in neutral behavior. See CROSSED_DESIGN.md. Do not report deterministic routing consequences as learned effects or independent model samples.
