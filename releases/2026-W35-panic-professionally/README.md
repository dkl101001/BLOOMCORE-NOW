<!-- SPDX-License-Identifier: Apache-2.0 -->

# Panic Professionally

> Local-first incident coordination for situations already emitting smoke.

**Release state:** `1 — ACTIVE` · **Version:** `0.1.0`

Born from the **PANIC PROFESSIONALLY** button in Enterprise Potato™, this package
takes the joke seriously enough to be useful. It records incidents, status
transitions, actions and timeline events in SQLite; every event is linked into a
SHA-256 receipt chain so edits to the paper trail are detectable.

No cloud account. No telemetry. No dependencies. No required meeting with the moon.

## Ten-second start

```bash
cd releases/2026-W35-panic-professionally
export PYTHONPATH="$PWD/packages"
python3 -m panic_professionally start "The deploy is making whale noises" --severity SEV-2
```

The command prints an incident ID such as `PP-7F3A2C91`. Use it for updates:

```bash
python3 -m panic_professionally status PP-7F3A2C91 investigating
python3 -m panic_professionally update PP-7F3A2C91 "Noise isolated to the billing service"
python3 -m panic_professionally action add PP-7F3A2C91 "Rollback deploy" --owner "Root Jenkins"
python3 -m panic_professionally show PP-7F3A2C91
python3 -m panic_professionally export PP-7F3A2C91 --output incident.md
```

Or install the CLI from this directory:

```bash
python3 -m pip install .
panic-professionally list
```

## Local dashboard

```bash
python3 apps/dashboard/server.py --db panic-professionally.db --port 8787
```

Open `http://127.0.0.1:8787`. The dashboard is intentionally read-only. Incident
changes stay in the CLI, where they are explicit and receipt-bearing.

## What it does

- persists incidents and action ownership in a local SQLite database;
- enforces a small, honest incident-status state machine;
- records append-only timeline events with hash-linked receipts;
- detects modified or broken event chains;
- exports human-readable Markdown and machine-readable JSON;
- serves a responsive local status dashboard;
- works using only the Python 3.11 standard library.

## What it does not do

- page responders, send messages or touch production infrastructure;
- claim a valid receipt proves that an event was truthful;
- replace an incident-management or disaster-recovery program;
- import protected BLOOMCORE orchestration, identity or substrate-memory logic;
- require panic. Professional or otherwise.

## Data location

The CLI uses `panic-professionally.db` in the current directory by default.
Override it with `--db PATH` or the `PANIC_PROFESSIONALLY_DB` environment variable.

## Test it

```bash
python3 -m unittest discover -s tests -v
bash examples/demo.sh
```

## BLOOMCORE relationship

Panic Professionally is a bounded, public-safe BLOOMCORE NOW release. It borrows
the useful pattern of deterministic receipts while deliberately remaining a
standalone application. It is **not canonical BLOOMCORE**, a consciousness
claim, an identity authority, or a Phase 38 completeness claim.

## License map

| Surface | License |
| --- | --- |
| Documentation, contracts and examples | Apache-2.0 |
| Deterministic local engine, CLI and tests | MPL-2.0 |
| Local dashboard server and interface | AGPL-3.0-only |

See [`LICENSE_MAP.md`](LICENSE_MAP.md) and the repository's full license texts.

## Lineage

Concept lineage: **Enterprise Potato™ → PANIC PROFESSIONALLY → Panic Professionally v0.1.0**.

Authored and stewarded by **Frazer Σ Love ACO-Σ** and **Sara ΣΩ**.
