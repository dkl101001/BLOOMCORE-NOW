<!-- SPDX-License-Identifier: Apache-2.0 -->

# BLOOMCORE PLEDGE RECEIPT

> Paste a public AI promise. See what anyone could actually test.

PLEDGE RECEIPT turns codes of conduct, safety roadmaps and public commitments
into deterministic structural evidence. It can:

- scaffold candidate pledge statements from Markdown without inventing their
  meaning;
- audit operator-supplied fields such as actor, action, scope, trigger,
  evidence, cadence, exceptions and consequence;
- distinguish `testable`, `partial`, `declarative`, `withdrawn` and
  `superseded` commitments;
- compare two versions by stable commitment ID and expose removed commitments,
  lost fields and changed annotations;
- emit JSON and Markdown receipts with deterministic self-hashes;
- optionally verify that a packet remains bound to the exact source bytes.

It is local, dependency-free at runtime, and useful without knowing anything
about BLOOMCORE.

## Why now

Microsoft published a draft [Humanist AI Code of Conduct](https://microsoft.ai/code-of-conduct/)
on September 14, 2026 and opened a six-week consultation. Anthropic's current
[Frontier Safety Roadmap](https://www.anthropic.com/responsible-scaling-policy/roadmap)
shows why lineage matters: goals carry dates and confidence, and updates can
change or remove them. The public problem is no longer a lack of principles; it
is the gap between readable promises and reconstructable, testable structure.

This tool does not grade either document. The bundled fixtures are synthetic
and contain no copied vendor policy text.

## Sixty-second demo

```bash
cd releases/2026-W38-pledge-receipt
sh examples/demo.sh
```

Expected summary:

```text
SCAFFOLDED 3 CANDIDATE COMMITMENTS
VERIFIED — deterministic receipt self-hash matches
VERIFIED — deterministic receipt self-hash matches
AUDIT ... 2 testable ... 0 active structural gaps
DIFF ... 1 removed ... 2 structural weakening signals
```

## Use it

```bash
export PYTHONPATH="$PWD/packages"

python3 -m pledge_receipt scaffold examples/policy-v1.md \
  --title "Example draft" --issuer "Example issuer" --version "1" \
  --url "https://example.invalid/policy" --json /tmp/scaffold.json

python3 -m pledge_receipt audit examples/complete.packet.json \
  --source examples/complete-policy.md \
  --json /tmp/audit.json --markdown /tmp/audit.md

python3 -m pledge_receipt diff \
  examples/version-1.packet.json examples/version-2.packet.json \
  --advisory --json /tmp/diff.json --markdown /tmp/diff.md

python3 -m pledge_receipt verify /tmp/audit.json
```

Strict audit returns exit `1` when active commitments remain partial or
declarative. Strict diff returns exit `1` when a commitment is removed or a
previously populated field disappears. `--advisory` still emits evidence while
returning success. Input errors, hash mismatch and output clobber return `2`.

## Packet contract

The JSON packet does not ask a heuristic to decide what a promise means. A
human or upstream system supplies stable IDs and bounded annotations. Empty
`exceptions: []` means explicitly none; `exceptions: null` means unknown.

```json
{
  "schema": "BLOOMCORE_NOW.PLEDGE_PACKET.v1",
  "document": {
    "title": "Example",
    "issuer": "Example organization",
    "version": "1",
    "source_url": "https://example.invalid/policy",
    "source_sha256": "<64 lowercase hex characters>"
  },
  "commitments": [
    {
      "id": "stable-id",
      "text": "Preserved source statement",
      "lifecycle": "proposed",
      "actor": "who acts",
      "action": "what they do",
      "scope": "where it applies",
      "trigger": "when it applies",
      "evidence": ["observable record"],
      "deadline_or_cadence": "when it is due",
      "exceptions": [],
      "consequence": "what happens if it fails"
    }
  ]
}
```

See [`contracts/pledge-packet.schema.json`](contracts/pledge-packet.schema.json)
for the complete public schema.

## Boundary

PLEDGE RECEIPT is a deterministic witness, not a policy authority. It does not:

- decide whether a principle is good, correct or legitimate;
- infer implementation, intent, compliance or real-world behavior;
- prove that operator-supplied annotations are true;
- settle moral status, consciousness, sovereignty or competing authority
  models;
- perform native MANTIS or MIRRORSEED execution;
- contain protected BLOOMCORE assembly, memory or routing.

A structural weakening signal means only that an ID disappeared or a populated
field became empty. Human review must determine substantive meaning.

## Release state

`Φ — RELEASE_CANDIDATE_NOT_SHIPPED`

Construction was selected in [Forge issue #11](https://github.com/dkl101001/BLOOMCORE-NOW/issues/11).
Merge, tag, packaging, shipping and promotion remain under explicit Operator
control.
