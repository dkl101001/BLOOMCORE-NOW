<!-- SPDX-License-Identifier: Apache-2.0 -->

# Research Evidence — 2026-W37

Evidence was inspected September 7, 2026. Dates describe publication or current
inspection, not timeless validity.

## Selected problem

- CISA published the [2026 Minimum Elements for an SBOM](https://media.defense.gov/2026/Jul/29/2003971159/-1/-1/1/CSI_2026_cisa_sbom_minimum_elements_508c.PDF)
  on July 29, 2026. The document replaces the 2021 baseline, adds document,
  component-hash and component-license fields, and emphasizes explicit unknowns
  and machine-processability.
- The public [sbt-sbom issue #259](https://github.com/sbt/sbt-sbom/issues/259),
  opened August 5, 2026, asks maintainers to evaluate generated output against
  the new requirements. That is direct practitioner evidence that the updated
  profile created implementation work.
- Existing tools such as [CycloneDX sbom-utility](https://github.com/CycloneDX/sbom-utility)
  already validate schemas and apply custom policies. This is strong substitute
  evidence and is why the commercial disposition is WATCH, not PRIORITY.

## Retention candidate

- [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data)
  distinguish abuse-monitoring logs, application state, endpoint behavior,
  approval-gated ZDR/MAM and third-party MCP retention.
- [Anthropic retention documentation](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data)
  and its [ZDR scope](https://privacy.claude.com/en/articles/8956058-i-have-a-zero-data-retention-agreement-with-anthropic-what-products-does-it-apply-to)
  also distinguish default deletion, saved chats, safety exceptions and
  approved product coverage.

The pain is current and consequential, but policy volatility and
contract-specific interpretation keep the build liminal and commercial state at
WATCH.

## MCP candidate

- The Cloud Security Alliance's [May 4, 2026 MCP security note](https://labs.cloudsecurityalliance.org/research/csa-research-note-mcp-security-crisis-20260504-csa-styled/)
  describes command injection, tool poisoning, definition rug pulls,
  authorization gaps, inventory and schema-hash controls.
- CoSAI's [practical MCP security guide](https://www.coalitionforsecureai.org/securing-the-ai-agent-revolution-a-practical-guide-to-mcp-security/)
  recommends strict schemas, sandboxing, inventory, observability and controls
  outside LLM judgment.
- Current [practitioner discussion](https://www.reddit.com/r/cybersecurity/comments/1pqst04/new_attack_vector_mcp_tool_poisoning_anyone/)
  specifically asks for integrity validation, permission boundaries and
  definition review.

The buyer and payment path are credible, but weekly build readiness remains
liminal until host formats and false-positive boundaries are fixed.

