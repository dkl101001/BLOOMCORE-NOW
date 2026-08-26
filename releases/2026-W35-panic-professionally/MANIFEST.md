<!-- SPDX-License-Identifier: Apache-2.0 -->

# Manifest

## Included

- `packages/panic_professionally/` — SQLite engine, receipts, state rules and CLI
- `apps/dashboard/` — read-only local dashboard
- `contracts/` — public incident JSON schema
- `docs/` — operating flow and evidence/security boundaries
- `examples/demo.sh` — runnable Enterprise Potato incident
- `tests/` — lifecycle, transition, tamper-detection and export tests
- `README.md` — user and boundary documentation
- `LICENSE_MAP.md` — per-surface licensing
- `NOTICE` — authorship, lineage and bundled-component notice
- `PUBLIC_BOUNDARY.yml` — public/private declaration
- `RELEASE_RECEIPT.md` — validation result
- `INTEGRITY_RECEIPT.json` — deterministic file hash manifest generated after validation

## Excluded

- protected BLOOMCORE orchestration and identity-bearing runtime material;
- messaging, paging, cloud integrations and production credentials;
- private datasets, historical logs and unrelated intellectual property.
