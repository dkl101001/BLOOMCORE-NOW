<!-- SPDX-License-Identifier: Apache-2.0 -->

# Panic Professionally v0.1.1

Panic Professionally v0.1.1 is a maintenance update to the August 2026
`V3.0` / v0.1.0 release. The original tag, release page, and attached ZIP are
preserved unchanged.

## Maintenance changes

- makes CLI action-assignment output safe on restricted Windows encodings;
- opens the dashboard database in true SQLite read-only mode;
- ships the dashboard command and interface in the installable wheel;
- includes complete MPL-2.0 and AGPL-3.0-only license texts and package metadata;
- adds a cross-platform synthetic operational demo;
- adds regression coverage for dashboard non-mutation, missing databases,
  installed commands, tamper handling, and console compatibility;
- states the receipt-chain boundary accurately: an external chain-head anchor
  is required to detect complete chain replacement or trailing-suffix removal.

## Install

Requires Python 3.11 or later.

```bash
python -m pip install panic_professionally-0.1.1-py3-none-any.whl
panic-professionally --help
panic-professionally-dashboard --help
```

The release ZIP is self-contained source and includes the CLI, read-only
dashboard, tests, documentation, license texts, integrity receipt, and both
demonstrations. See the root `README.md` inside the ZIP for the full operating
guide and boundaries.

## Verification

Fresh verification evidence and reproducible commands are recorded in
`docs/RELEASE_READINESS_2026-09-30.md`. Artifact SHA-256 values are published
alongside the GitHub release assets.

This release does not add cloud accounts, telemetry, paging, messaging,
production integrations, or protected BLOOMCORE runtime material.
