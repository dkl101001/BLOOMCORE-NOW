<!-- SPDX-License-Identifier: Apache-2.0 -->

# Threat model

## Protected by this build

- deterministic parsing with duplicate-key and non-finite-number rejection;
- five MiB per-input and 50,000-event limits;
- relative-path containment checks for file targets;
- exact schemas and no-clobber output;
- receipt and manifest hashes plus bounded-claim invariant verification;
- replay from original inputs.

## Not protected by this build

- forged, truncated, reordered, or selectively captured source traces;
- compromise of the trace producer or policy author;
- semantic equivalence between a logged target and a real resource;
- command parsing beyond declared string-pattern comparison;
- time ordering, concurrency, causality, or cross-run identity;
- live containment, telemetry collection, signature verification, or response.

Use trusted trace collection and a real enforcement layer where prevention is
required. Do not put secrets or raw file contents in the trace.

