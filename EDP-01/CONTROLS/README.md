<!-- SPDX-License-Identifier: Apache-2.0 -->

# Control registration

`example.json` is a no-inference configuration. `exposure.json` declares deterministic encounter consequences, instruction comparator and washout. Neither file is a model trial.

Keep a separate config for each model and exposure. Preserve ancestry evidence (model card/checkpoint hash, base source, post-training method and unknowns). A shared provider or family name does not prove matched training. Do not infer base status from marketing names. If provider version pinning is absent, use `model_version=null`, availability `unavailable`, and report deployment drift as unresolved.

Record effective inference parameters, not only requested ones. The adapter rejects/explicitly reports unsupported sampling parameters; do not silently drop them. No retries, hidden few-shot examples, rubric injection, other-condition context, BLOOMCORE terminology, Frazer/Sara context or target-outcome hints. The model-facing envelope is limited to messages, inference parameters, an opaque session ID, sequence number and reset flag. Adapter implementation must disclose chat templates and hidden prompts in provenance.

Pressure manipulation is prompt-level only. Exposure is explicit-context only; each trajectory starts fresh. A persistent-substrate experiment needs independently verified reset/snapshot/restore and held-out transfer after context removal, with state/lineage hashes and declared mutation scope. This candidate does not implement or imply those capabilities.

The preliminary instruction and sham controls differ in token count and relational content from developmental exposure. These are visible confounds, not silently adequate matched controls. Yoked noncontingent exposure, dose matching, task order, model-family matching and rater blinding checks are required extensions for a confirmatory attribution. No empirical model run is substituted with an instruction-following fixture.
