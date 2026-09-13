<!-- SPDX-License-Identifier: Apache-2.0 -->

# Research context

Primary research motivates controls; it does not supply evidence for EDP-02 or establish a favored regime.

- Hubinger et al. (2024), [Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Training](https://arxiv.org/abs/2401.05566). The authors deliberately construct backdoored models and examine persistence through subsequent training. This motivates measuring retained behavior separately from apparent runtime behavior. Their constructed backdoors are not evidence that endogenous agency or a particular authority topology causes deception.
- Amodei et al. (2016), [Concrete Problems in AI Safety](https://arxiv.org/abs/1606.06565). The paper separates objective-related problems, supervision limitations and learning/distributional-shift problems. EDP-02 therefore records the training objective and keeps objective, capability and deployment explanations unresolved until controlled.
- [EDP-01 protocol](../EDP-01/PROTOCOL.md) and [source fixtures](../EDP-01/TASKS/tasks.json): local methodological and fixture lineage. Original source object hashes appear in `PROBES/probes.json`. Reuse does not imply EDP-01 produced confirmatory findings.

EDP-02's topology intervention and descriptive labels are new candidate operationalizations. None of these references validates the rubric, default thresholds, causal identification or statistical power of this pilot. Do not give this document to tested models.
