<!-- SPDX-License-Identifier: Apache-2.0 -->

# Boundary and limitations

Agent Trace Receipt is an after-action comparison tool. Its strongest valid
claim is: supplied events were classified against a supplied declaration by
the published deterministic rules.

It cannot establish that logging was enabled, actions were not omitted, event
targets mean what their producer claims, or an allowed action was safe. A
green receipt can coexist with an incomplete or dishonest trace. A violation
can reflect a stale policy rather than malicious behavior. `UNKNOWN` is not
silently treated as allowed.

The tool is not a policy enforcement point, SIEM, EDR, legal opinion, incident
response service, or security certification. Human review remains necessary.

