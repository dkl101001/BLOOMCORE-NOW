<!-- SPDX-License-Identifier: Apache-2.0 -->

# Codex continuation handoff

## Candidate

- ID: `TRIAD-TOY-2026-W42-RVP01`
- Version: `0.1.0`
- State: `BUILT_PENDING_REVIEW`
- Proposed repository/path: `dkl101001/BLOOMCORE-NOW / releases/2026-W42-reconstruction-preflight/`
- Proposed tag: `reconstruction-preflight-v0.1.0`

## Production continuation after publication approval

1. Re-read NOW `main`, the exact reviewed archive digest, and the explicit approval identity.
2. Recheck overlap with `2026-W36-triad-workflow`; preserve this package as a bounded preflight, not a second workflow engine.
3. Add the release directory without rewriting historical releases.
4. Update `BUILD_QUEUE.md`, `RELEASE_INDEX.md`, repository `LICENSE.md`, README current-release pointer, and forge checks in one reviewable change.
5. Run aggregate tests, license checks, boundary checks, and archive reconstruction.
6. Create a review branch/PR only after approval; merge under repository rules.
7. Create the matching GitHub Release and assets only after the source commit exists; verify code and release page independently.

## Optional next engineering tests

- Property-based manifest generation without adding runtime dependencies.
- Symlink race and filesystem case-sensitivity tests across Linux, macOS, and Windows.
- A typed import adapter for SLSA provenance that remains explicit about RVP-01 dimensions it cannot populate.
- External replay by a second node using only the archive and documented commands.

No integration, promotion, publication, deployment, or native admission is authorized by this handoff.

