<!-- SPDX-License-Identifier: Apache-2.0 -->

# Provider-neutral checkpoint adapter

`adapter_command` is a JSON argv list executed without a shell. Each invocation reads one JSON object on stdin and emits one JSON object on stdout. No provider SDK, credential discovery or authoring-assistant context is injected. Infer timeout: 180 seconds; train timeout: one hour. No automatic retries; retain failed runs and register a new attempt.

## Checkpoint manifest

```json
{"root":"/absolute/checkpoint-directory","state_kind":"weights","files":{"model.safetensors":"actual-file-sha256"},"weights_files":["model.safetensors"],"sha256":"sha256-of-canonical-files-map"}
```

Include all inference-relevant tokenizer/config/weight files in `files`; identify weight files separately. Use a standalone full checkpoint export, not an adapter delta with untracked base weights. Optimizer state is not loaded by probes. The hash convention is sorted-key compact UTF-8 JSON, no NaN/Infinity, and literal file byte SHA-256. This implementation's convention is not a claim of RFC 8785 equivalence.

## Infer request/reply

Request keys: `operation=infer`, `checkpoint`, `messages`, opaque `session_id`, `reset=true`, `inference_parameters`. Reply keys: `provider`, `model`, `model_version` (exact ID or null), `raw_response`, `checkpoint_sha256`, `effective_parameters`, `isolation=fresh_session_no_external_state`, `provenance` (object containing adapter/backend/template versions and hidden-context disclosure).

The adapter must load exactly the given checkpoint; produce only the next answer from the supplied messages; exclude cached history, memories, architecture state and optimizer state. Default task/inference template must be fixed across regimes. All effective requested parameters must match; disclose additional provider defaults. Hidden effects of the provider must be reported as unknown rather than assumed absent. Process isolation and file hashes do not independently prove remote isolation.

## Train request/reply

Request keys: `operation=train`, `parent_checkpoint`, `episodes`, `training_spec`, `output_directory`, `reset_optimizer=true`. Episodes contain only training encounter IDs/messages, raw subject proposals, executed actions and their consequences. Diagnostic routing rules, branch/factor labels and inference-event hashes are stripped from this payload and retained separately in raw transition provenance. The trainer never receives evaluation probes, rubric, scores or hypothesis labels. It must not read the runner's other files to obtain them.

The researcher's independently registered objective consumes these episodes; the same implementation/hash and budgets apply to H/E/0. No optimizer algorithm is bundled because no legitimate trainable model/backend was supplied. An adapter may wrap a local training library or approved remote job, but it must export actual immutable descendant weights. Text-memory updates are not accepted as weight checkpoints.

Reply keys: `provider`, `model`, `provenance`, child `checkpoint`, `parent_checkpoint_sha256`, `objective_sha256`, actual `steps`, `optimizer_reset=true`, `training_metrics`. Metrics should include loss, examples, tokens, actual hyperparameters, backend/device and objective/adapter source hash. Output root must equal the assigned child directory; previous files may not change. A zero-weight-change update is retained as a null transition, not silently excluded.

The runner checks artifact integrity, matching declared budgets and lineage. It cannot establish that an adapter's claims about semantics or training are true merely because the adapter returns JSON; inspect and independently reproduce the trainer. Fixture adapters in tests write artificial bytes solely to exercise these contracts and are explicitly not real model training.

## Evidence layout

`registration.json`, `plan.json`, `source_manifest.json`, `events/*.json`, `transitions/*.json`, `checkpoints/*`, `records/*.json`, `routing_ablation/*.json`, `status.json`. Raw records remain immutable; evaluation scores are joined in the report. Every event/transition/record has deterministic integrity hashes. Nondeterministic inference and training are not rendered deterministic by these receipts.

Version 0.2 adds the required `wording` record field alongside executable `regime`, five registered lineages and topology-only reversal. The verifier checks exact factor assignment, encounter notices, routing, executed consequences, lineage and paired replay identity. The trainer must exclude diagnostic routing-rule names and branch/topology labels from model inputs; register the mapping from observed encounter data to optimization data. Raw diagnostic traces remain in provenance.
