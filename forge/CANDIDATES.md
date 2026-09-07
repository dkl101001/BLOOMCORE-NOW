<!-- SPDX-License-Identifier: Apache-2.0 -->

# 2026-W37 Candidate Triage

Exactly three candidates were evaluated. Forge state and commercial
disposition are independent routing surfaces.

| Candidate | Pain | Legibility | Demo | Build | BLOOMCORE fit | Boundary | Forge state | Commercial disposition |
|---|---:|---:|---:|---:|---:|---:|---|---|
| BLOOMCORE SBOM RECEIPT | 5 | 5 | 5 | 5 | 5 | 5 | **1 — ACTIVE** | **COMMERCIAL_WATCH** |
| AI RETENTION RECEIPT | 5 | 5 | 5 | 3 | 5 | 4 | **Φ — LIMINAL** | **COMMERCIAL_WATCH** |
| MCP TOOLPRINT | 5 | 5 | 5 | 4 | 5 | 4 | **Φ — LIMINAL** | **COMMERCIAL_PRIORITY** |

## One-sentence legibility

1. **SBOM RECEIPT:** Drop in CycloneDX JSON and get a deterministic receipt
   showing which CISA 2026 minimum-element fields are present, missing,
   explicitly unknown or not machine-verifiable.
2. **AI RETENTION RECEIPT:** Compare an AI workload's provider and endpoints
   against current retention declarations and expose persistence, ZDR gaps and
   third-party exceptions.
3. **MCP TOOLPRINT:** Snapshot and hash MCP tool definitions and permissions,
   then flag capability drift and high-risk shell, network and secret
   combinations before agent startup.

## Independent decision

SBOM RECEIPT is `1 — ACTIVE` for construction because its official source is
current, its structural scope is deterministic, and its limitations can be
demonstrated in under one minute. It remains `COMMERCIAL_WATCH`: procurement
pain is credible, but the market is crowded and a file-only tool cannot prove
process practices.

MCP TOOLPRINT is `COMMERCIAL_PRIORITY` but remains `Φ — LIMINAL` in the weekly
Forge. Its buyer and payment path are stronger, while live discovery formats,
host integration and false-positive boundaries need a dedicated commercial
thread before construction. Commercial priority does not override build
readiness.

Scores are selection aids, not objective truth, commercial validation or
release authority. Evidence and extraction records are preserved in
`COMMERCIAL_CANDIDATE_BANK.md` and GitHub issue #9.
