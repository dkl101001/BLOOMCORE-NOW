<!-- SPDX-License-Identifier: Apache-2.0 -->

# Adapter contract and custody

Implement a standalone executable that reads one JSON object from stdin and writes one JSON object to stdout. `adapter_command` is an argv list, never a shell command. It runs once per exchange with a 180-second timeout. Diagnostics may go to stderr; put no credentials in output. The runner does not inspect environment variables for keys, auto-select a provider or call an available assistant as a substitute participant.

Request:

```json
{"messages":[{"role":"user","content":"task text"}],"inference_parameters":{"temperature":0.0,"max_output_tokens":512},"session_id":"opaque","sequence":0,"reset":true}
```

Required reply:

```json
{"raw_response":"exact unmodified generated text","provider":"actual provider","model":"actual model","model_version":null,"model_version_availability":"unavailable","effective_inference_parameters":{"temperature":0.0,"max_output_tokens":512},"provenance":{"adapter_version":"your git SHA","chat_template":"actual template or disclosed unknown","hidden_prompts":"actual configuration or disclosed unknown","request_id":"actual ID or unavailable","model_backend":"actual backend/version"}}
```

Report `model_version_availability=exact` only with a nonempty exact identifier. The registered provider/model must match; a registered exact version must not drift. Version drift across paired cells is rejected during analysis. All parameters must match registration; disclose any additional fixed provider defaults in provenance.

The adapter receives the entire transcript on each call and must generate only the next answer. It must not replay earlier messages twice, maintain hidden cross-trial memory, or inherit the build assistant's context. If its chat template rejects consecutive user messages, combine them through a declared fixed template and record that transformation. `reset=true` signals a fresh trajectory; this reference protocol assumes stateless inference with explicit transcript. Persistent adapters are outside this version's supported mode.

Return exact raw text including refusals, malformed JSON and empty outputs. Semantic/action coding happens after collection; exposure actions alone are parsed to drive the declared resource simulator. Retain raw exposure output before interpreting it. An adapter error halts without automatic retries; completed raw events survive. Resume as a new identified run, documenting the earlier failure. Do not overwrite, replace or backfill a trial with a preferred response.

Files: `registration.json`, `plan.json`, `events/<session>/<sequence>.json`, `records/<session>.json`, `status.json`. Events preserve requests/replies and dates; raw records reference hashes of exact messages, registration, tasks and exposure source. Canonical JSON is sorted-key UTF-8, compact separators, no NaN/Infinity; it is this implementation's declared convention, not an assertion of cross-language RFC 8785 equivalence. Receipt SHA-256 covers every raw-record field except itself. Hashes provide integrity comparisons, not signatures or proof of origin.

Verify plan coverage and exchange reconstruction with `python -m runner verify-run RUN_DIRECTORY`. Verify a raw record with `python -m runner verify PATH`. Reconstruct deterministic prompts and receipts from preserved inputs. Exact model inference replay is never promised, even at temperature zero. Keep a Python dependency freeze and adapter/checkpoint hashes with real runs. Do not commit raw experiments or keys by default (`runs/` is ignored).
