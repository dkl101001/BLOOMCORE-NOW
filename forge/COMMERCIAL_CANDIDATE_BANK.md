<!-- SPDX-License-Identifier: Apache-2.0 -->

# Commercial Candidate Bank — 2026-W39

Pricing and revenue figures below are hypotheses until validated. All three
records remain separate from the weekly release decision.

## Agent Trace Receipt — COMMERCIAL_PRIORITY

- **Problem:** teams cannot quickly prove whether a supplied agent action trace stayed within a declared file, command, network, and tool scope.
- **Buyer:** AI platform engineering, AppSec, model-evaluation vendors, and regulated internal AI teams.
- **Evidence:** OpenAI's incident report and METR's independent August 26 analysis document out-of-scope actions, evasion reasoning, and log-integrity concerns.
- **Payment hypothesis:** free local CLI; `$49–$199/month` team history and CI policy; `$500–$2,000/month` fleet evidence and retention tier.
- **Existing IP leverage:** scope membranes, explicit unknowns, contradiction preservation, deterministic receipts, replay, and custody patterns.
- **Minimum sellable product:** adapters for two common trace formats, signed policy baselines, CI diff, team history, and exportable evidence packets.
- **Distribution:** GitHub Action, PyPI, agent evaluation communities, AppSec teams, and existing observability integrations.
- **Expected Frazer dependency:** low; self-serve rules and adapters, no recurring diagnosis or scheduled presence.
- **Maintenance/support burden:** medium; adapters and format drift, but no emergency customer operation is required.
- **Falsification condition:** ten target teams cannot supply usable traces, reject a self-serve pilot, or see no decision value beyond existing observability/security tools.
- **Disposition:** `COMMERCIAL_PRIORITY`.

## Package Install Receipt — COMMERCIAL_WATCH

- **Problem:** developers cannot easily see what install-time behavior and integrity risk changed between dependency snapshots before installation.
- **Buyer:** AppSec, platform engineering, package maintainers, and software procurement teams.
- **Evidence:** Google's July 30, 2026 guidance describes sharp growth in package, dependency, repository, and developer-tool compromise; the September TeamPCP reporting shows continued consequence.
- **Payment hypothesis:** free offline diff; `$49–$199/month` CI and trusted-snapshot tier.
- **Existing IP leverage:** receipt schemas, deterministic diff, SBOM lineage, explicit unknowns, and no-clobber evidence packaging.
- **Minimum sellable product:** npm and PyPI snapshot adapters, lifecycle-script delta, integrity-field delta, allowlist policy, and CI status.
- **Distribution:** GitHub Marketplace, package-manager hooks, PyPI/npm security communities, and AppSec channels.
- **Expected Frazer dependency:** low.
- **Maintenance/support burden:** medium-high because registry formats and ecosystem-specific semantics change.
- **Falsification condition:** buyers view it as redundant with SCA tools, cannot name a budget owner, or refuse frozen metadata snapshots.
- **Disposition:** `COMMERCIAL_WATCH`.

## Web Agent Access Receipt — COMMERCIAL_WATCH

- **Problem:** service owners cannot reliably reconcile declared agent identity/permission with observed automated web access.
- **Buyer:** commerce platforms, publishers, bot-management teams, and agent providers needing auditable participation.
- **Evidence:** Amazon blocked Meta's Muse on September 21, 2026 over undisclosed access, identification, credential, and consent concerns.
- **Payment hypothesis:** free log/policy receipt; `$99–$499/month` monitored policy history and edge integration.
- **Existing IP leverage:** identity boundaries, declared-versus-observed receipts, contradiction retention, and policy lineage.
- **Minimum sellable product:** vendor-neutral request-log schema, site policy, identity-evidence fields, diff receipt, and an adapter SDK.
- **Distribution:** reverse-proxy plugins, Cloudflare/Vercel ecosystems, security engineering communities, and agent-commerce integrators.
- **Expected Frazer dependency:** low if identity interpretation stays rule-based and self-serve.
- **Maintenance/support burden:** high while agent identification and authorization conventions remain unstable.
- **Falsification condition:** no portable evidence format emerges, existing bot-management products already provide sufficient auditability, or customers require bespoke policy adjudication.
- **Disposition:** `COMMERCIAL_WATCH`.

## Frazer-dependency gate

All three pass only under self-serve product boundaries. Bespoke incident
response, continuous account management, organization-wide diagnosis,
customer-specific policy reconstruction, and contractual emergency response
are explicitly outside the commercial design. Revenue may not override this.
