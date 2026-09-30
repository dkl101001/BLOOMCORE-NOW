<!-- SPDX-License-Identifier: Apache-2.0 -->

# 2026-W39 Candidate Triage

Exactly three candidates were evaluated. Scores are aids, not truth claims or
release authority.

| Candidate | One-sentence promise | Pain | Legibility | Demo | Build | Fit | Boundary | Forge state | Commercial disposition |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| Agent Trace Receipt | Compare a declared agent scope with a JSONL action trace and expose allowed, violating, and unknown events. | 5 | 5 | 5 | 5 | 5 | 5 | `1 — ACTIVE` | `COMMERCIAL_PRIORITY` |
| Package Install Receipt | Compare package metadata snapshots and surface new install scripts, integrity drift, and dependency risk before installation. | 5 | 5 | 5 | 3 | 4 | 5 | `Φ — LIMINAL` | `COMMERCIAL_WATCH` |
| Web Agent Access Receipt | Compare a site's agent-access policy with HTTP request evidence and expose unidentified or unauthorized automation. | 5 | 5 | 5 | 3 | 4 | 4 | `Φ — LIMINAL` | `COMMERCIAL_WATCH` |

## Independent state reasoning

Agent Trace Receipt is active for construction because it can be useful today
as a passive, format-bounded local tool. It does not need live probes,
credentials, platform access, or protected BLOOMCORE assembly.

Package Install Receipt remains liminal because a useful result needs a stable,
portable metadata snapshot contract; querying mutable registries during audit
would weaken determinism. Google Threat Intelligence Group reported on July 30
that major open-source supply-chain campaigns expanded sharply through 2026,
including dependency and developer-tool compromise, so the problem remains
high-value despite the unresolved intake boundary.

Web Agent Access Receipt remains liminal because the current pain is legible—
Amazon blocked Meta's Muse agent on September 21 over disclosure,
identification, credential, and participation concerns—but portable agent
identity and authorization evidence is not yet settled enough for an honest
minimum build.

Commercial state did not choose the weekly build. The active candidate was
selected by evidence, public safety, bounded feasibility, and demonstrability.

## Evidence

- [OpenAI incident report](https://openai.com/index/hugging-face-incident-and-the-road-ahead/)
- [METR independent investigation](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/)
- [Google Threat Intelligence Group supply-chain guidance, July 30, 2026](https://cloud.google.com/blog/topics/threat-intelligence/mitigation-guidance-for-supply-chain-compromise)
- [Google/Mandiant agentic source-review report, August 18, 2026](https://cloud.google.com/blog/topics/threat-intelligence/staying-ahead-of-adversarial-ai-through-agentic-source-code-review)
- [Amazon/Meta Muse report, September 21, 2026](https://www.theverge.com/tech/998078/amazon-blocks-meta-muse-ai-agent-shopping)
- [Public programming discussion of the OpenAI/Hugging Face incident](https://www.reddit.com/r/programming/search/?q=OpenAI%20Hugging%20Face%20incident&restrict_sr=1)
