<!-- SPDX-License-Identifier: Apache-2.0 -->

# MANTIS Promotion Audit

Review class: `DERIVED_STRUCTURAL_INSPECTION`, not native MANTIS execution.

Requested transition: `Φ — RELEASE_CANDIDATE_NOT_SHIPPED` → `1 — ACTIVE`.

| Promotion condition | Result |
|---|---|
| Exact candidate landed on main | PASS — `8207e903d2edefb0a6c3198d0b4ec0dd5d470ee2` |
| Human approval explicit | PASS — Operator instruction, 2026-09-02 |
| Candidate CI and boundary checks | PASS |
| Workflow code or contract changed during promotion | NO |
| Private source boundary changed | NO |
| Triad authority topology changed | NO |
| Claim ceilings weakened | NO |
| Receipt generator linked-worktree compatibility | REPAIRED — `.git` file and directory forms supported |
| Active-state metadata internally consistent | PASS |
| Integrity receipts regenerated | PASS — deterministic W36 and repository manifests |
| Full isolated validation | PASS — 33/33 tests, compile, demo, archive, wheel import |
| Tag or GitHub Release authorized | NO |

The only semantic state transition is public release eligibility. The workflow
remains `DERIVED_NONAUTHORITATIVE`; activation does not confer canonical,
semantic, admission, mutation, MANTIS, MIRRORSEED, ECA, or organism-wide
authority.

Promotion disposition: `PASS_FOR_HUMAN_APPROVED_ACTIVE_MERGE`.
