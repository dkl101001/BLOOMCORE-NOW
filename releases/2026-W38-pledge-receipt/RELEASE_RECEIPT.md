<!-- SPDX-License-Identifier: Apache-2.0 -->

# Release Receipt — BLOOMCORE PLEDGE RECEIPT v0.1.0

## State

- Forge: `1 — ACTIVE` for bounded construction
- Commercial: `COMMERCIAL_WATCH`
- Release: `Φ — RELEASE_CANDIDATE_NOT_SHIPPED`
- Operator approval: not granted

## Minimum useful result

The dependency-free Python CLI scaffolds candidate commitments from Markdown,
audits structured pledge packets, compares versions by stable ID and verifies
deterministic receipt hashes. The synthetic demo completes in under one second
and makes removed commitments and lost structure visible.

## Local evidence

- 14/14 W38 unit, adversarial and CLI tests passed.
- 33/33 previous weekly-release regressions passed.
- 62/62 EDP-01 and EDP-02 preservation tests passed.
- 109/109 full foundry tests passed.
- Python compilation, public/private boundary and license membranes passed.
- An offline-built wheel installed without runtime dependencies and emitted a
  self-verifying receipt.
- An isolated archive of the candidate commit replayed all 14 W38 tests, the
  sub-minute demo, wheel build, install, audit and self-hash verification.
- The GitHub CI and Boundary and License Membrane workflows passed, and the
  reviewed local and remote trees matched exactly.
- A missing fresh-environment dependency for EDP-01 was installed from that
  instrument's declared requirements; no validation scope was removed.

All bounded build obligations are closed. Operator approval and the commercial
hypotheses remain open; neither is implied by passing validation.

## Authority boundary

This receipt proves deterministic build evidence only. It does not prove that a
pledge is good, true, implemented, compliant or followed. It does not authorize
merge, tag, release, package publication, commercial promotion or deployment.
