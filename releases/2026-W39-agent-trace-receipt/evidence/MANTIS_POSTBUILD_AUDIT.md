<!-- SPDX-License-Identifier: Apache-2.0 -->

# Structural MANTIS Postbuild Audit

This is a derived structural review, not native MANTIS execution.

## Adversarial questions exercised

- Can malformed or duplicate-key JSON silently change meaning? Rejected.
- Can an absolute or parent-traversing file target appear allowed? Rejected.
- Can wildcard network policy accidentally authorize the apex? Tested against.
- Can unknown event kinds disappear into allowed counts? Preserved as unknown or fail-closed violation.
- Can a receipt be re-hashed after uplifting its claims? Bounded-claim invariants reject it.
- Can an output directory be silently overwritten? Rejected.
- Can extra run artifacts hide beside the receipt? Verification rejects them.
- Can large inputs expand without a bound? File and event limits are enforced.

## Preserved contradictions

- A green receipt is useful evidence but cannot prove trace completeness.
- A violation may represent agent drift or a stale declaration.
- String-pattern command policy is legible but not semantic command analysis.
- Passive auditing closes the unsafe-probe boundary but cannot prevent harm.

Disposition: **PASS_FOR_DRAFT_REVIEW_AT_PHI**, subject to recorded validation.

