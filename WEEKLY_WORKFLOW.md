<!-- SPDX-License-Identifier: Apache-2.0 -->

# Weekly Foundry Workflow

This file defines the operating contract for one integrated weekly Forge run.
Research, selection, construction and candidate handoff occur sequentially;
release authority remains separate.

## Stage 1 — Public Module Forge

1. Inspect current primary evidence for visible problems.
2. Produce exactly three bounded software candidates.
3. Check the existing release index and queue for duplication.
4. Score pain, legibility, demonstration, buildability, BLOOMCORE fit,
   boundary safety and adoption.
5. Preserve candidates as `0`, `Φ`, or `1`.
6. Evaluate commercial viability independently and apply the hard
   Frazer-dependency gate.
7. Bank every commercial priority or strong watch candidate without forcing it
   into the weekly build.
8. Do not select or build from private source until a public-safe extraction
   boundary is recorded.

## Stage 2 — Bounded build

1. Create one release directory from the template.
2. Implement a complete minimum useful program.
3. Assign file-level licenses before copying code across lanes.
4. Add tests, runnable examples, limitations and a one-minute demonstration.
5. Update the queue, release index and boundary receipt.

## Stage 3 — Test and candidate handoff

1. Run `python3 forge_tools/run_all_tests.py`.
2. Generate the release integrity receipt.
3. If any check fails, preserve a failure receipt and leave state `Φ`.
4. If every check passes, prepare a release candidate.
5. Open a draft pull request and require human approval before merge, tag,
   publication, shipping or promotion to release-active state.

## Non-negotiable exclusions

- Do not publish credentials, private data or protected BLOOMCORE assembly.
- Do not infer public safety from successful tests alone.
- Do not let receipt hashes imply truth, identity or semantic certification.
- Do not silently rename or flatten lineage-bearing architecture.
- Do not auto-publish from an unattended research or build run.
