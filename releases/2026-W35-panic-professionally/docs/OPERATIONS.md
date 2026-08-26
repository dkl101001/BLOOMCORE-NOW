<!-- SPDX-License-Identifier: Apache-2.0 -->

# Operations Guide

## Incident flow

```text
declared -> investigating -> identified -> monitoring -> resolved
     \----------------------------------------------------->
```

An incident may resolve early when the alarm is harmless. Monitoring may return
to investigating when the supposed fix develops opinions. Resolved incidents
are immutable in v0.1.0; create a new incident and reference the old ID if the
problem returns.

## Working rhythm

1. Declare one incident with a specific title, severity and commander.
2. Advance it to `investigating` when active work begins.
3. Record observations, decisions and changes as timeline events.
4. Give every executable action an owner—even if that owner is The Moon.
5. Mark the cause `identified`, then move to `monitoring` after mitigation.
6. Verify the receipt chain and export the report before resolution.

## Severity language

| Level | Working meaning |
| --- | --- |
| SEV-1 | Critical impact requiring immediate coordinated response |
| SEV-2 | Major impact with urgent response required |
| SEV-3 | Limited impact or degraded operation |
| SEV-4 | Minor problem, suspicious noise or bureaucratic weather |

These definitions are local defaults, not a replacement for an organization's
established incident policy.

## Backup and portability

All durable state lives in one SQLite file. Stop writes before copying it for a
consistent filesystem-level backup. JSON and Markdown exports are portable
reports; they do not replace the database or reconstruct its receipt chain.
