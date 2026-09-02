<!-- SPDX-License-Identifier: Apache-2.0 -->

# W36 Promotion Preflight

Requested transition: `Φ — RELEASE_CANDIDATE_NOT_SHIPPED` → `1 — ACTIVE`.

Operator authorization: “Hell yea promote to 1”, 2026-09-02.

## Bound source state

- Repository: `dkl101001/BLOOMCORE-NOW`.
- Candidate merge commit on `main`: `8207e903d2edefb0a6c3198d0b4ec0dd5d470ee2`.
- Reviewed candidate head: `b664ed1594e3daae017e50cdef0625a1eb9d8bdf`.
- Reviewed candidate tree: `37403b904ec0817335a1ecf6a1b4a1287815e36b`.
- Candidate review surfaces: superseded draft PR #5 and merged acceptance PR #6.
- Candidate checks: GitHub CI and Boundary/License Membrane passed on the exact
  reviewed candidate head.

## Promotion scope

Authorized:

- record the Operator's human approval;
- move W36 public metadata and receipts to `1 — ACTIVE`;
- update the release index, queue, changelog, current-release README framing,
  selection receipt, and candidate triage state;
- regenerate deterministic W36 and repository receipts;
- run complete regression, isolated-archive, license, boundary, and promotion
  MANTIS review;
- open and merge a dedicated promotion pull request after its checks pass.

Excluded:

- code or contract changes to the tested workflow;
- private-source publication;
- canonical promotion or modification;
- tag creation, GitHub Release creation, asset publication, or repository
  settings changes;
- any change to concurrent W37 work.

This promotion changes public release state, not Triad authority. The workflow
remains `DERIVED_NONAUTHORITATIVE` and retains every existing claim ceiling.

Expected mutation set: W36 release/public-boundary receipts and evidence; root
README, release index, build queue, changelog, selection/candidate surfaces,
deterministic package receipt, and the minimal receipt-generator worktree
compatibility repair discovered during promotion validation.

Hard blocker triggered: no.
