# Red Tape Dispenser + Transparency Desk

**Successor note:** v0.2 adds a native case editor and Windows file ACLs. Use
[the desktop guide](DESKTOP.md) for that workflow. The CLI reference below is
retained from v0.1; its statements that no graphical editor exists and that only
Linux permissions have been tested describe the original release.

Co-authored by **Frazer Σ Love ACO-Σ** and **Sara ΣΩ**.

An optional FLOCK OFF module that turns public records into concise town-hall questions and reconstructable accountability packets. It works locally with no accounts, remote AI, telemetry, sending, recording, or publishing.

## Run the fictional example

From the installed repository:

```sh
flockoff red-tape --db work/accountability.sqlite --key work/accountability.key init
flockoff red-tape --db work/accountability.sqlite --key work/accountability.key import docs/red_tape/examples/case.json --expected-revision 0
flockoff red-tape --db work/accountability.sqlite --key work/accountability.key check demo-city-001
flockoff red-tape --db work/accountability.sqlite --key work/accountability.key review demo-city-001 --reviewer "Example reviewer" --attest-premises --attest-contrary-evidence --attest-meeting-rules
flockoff red-tape --db work/accountability.sqlite --key work/accountability.key dispense demo-city-001 --as-of 2026-10-27 --output work/packet-001 --ready --humor
flockoff red-tape --db work/accountability.sqlite --key work/accountability.key verify-packet demo-city-001 --directory work/packet-001
```

Open `work/packet-001/town_hall.html` in a browser. It is self-contained and has no remote assets or network requests. It includes a user-started timer, print button, and one expandable clarification per selected question. The fictional URLs and meeting-rule assertions are examples only; replace and verify them before real use.

The separate `flockoff-red-tape` executable accepts the same arguments after `red-tape`. For source-only execution, use `PYTHONPATH=src python3 -m flockoff.cli red-tape ...`.

## Outputs

- `speaking_brief.txt`: selected decision, up to three questions, requested action, material qualifications.
- `evidence_appendix.txt`: original sources, exact locators, public-document hashes when supplied, lineage, limitations, claims, and contrary records.
- `assessment.txt`: all twelve Transparency Impact Assessment questions and recorded states.
- `answer_tracker.json`: complete selected-question answer histories, commitments, unresolved gaps, and chosen request-review reminders.
- `town_hall.html`: accessible offline presentation and print layout.
- `packet_receipt.json`: exact custody revision, rendering parameters, module-source digest, and output hashes.

The brief must fit the 400-word maximum and, when an allowance is supplied, an estimated 120-wpm read with 20% time reserved for pauses. This only gates the drafting budget. Rehearse and inspect print preview; physical one-page fit is not certified.

## Retain documents and revise the packet

```sh
# Attach an existing public document; original bytes are retained encrypted.
flockoff red-tape --db work/accountability.sqlite --key work/accountability.key attach demo-city-001 E01 /path/to/public-contract.pdf

# Create a restricted plaintext editing copy. Keep it off shared drives.
flockoff red-tape --db work/accountability.sqlite --key work/accountability.key checkout demo-city-001 --output work/edit.json

# Edit the JSON, then import with the revision returned by attach/checkout.
flockoff red-tape --db work/accountability.sqlite --key work/accountability.key import work/edit.json --expected-revision 3
```

The example revision number assumes the earlier commands ran once and the attachment made revision 3; always use the actual receipt. Import rejects stale revisions. Changes carrying an unchanged old review remove that review. Answer entries cannot be rewritten: append a correction with a new ID. Prior source, claim, assessment, and request states remain reconstructable in earlier encrypted snapshots. Re-review and dispense into a new directory.

`document CASE SOURCE --output PATH` retrieves an attached original as a restricted local copy. A source hash alone does not mean the original has been attached. Superseded source metadata must point to another recorded source, and use of a superseded premise blocks ready status until revised. Amendment resolution is reviewed by a human; the software does not interpret contracts.

## Record an answer

```sh
flockoff red-tape --db work/accountability.sqlite --key work/accountability.key answer demo-city-001 docs/red_tape/examples/answer.json
```

Use new IDs for new answers and corrections. Entries explicitly distinguish quotes, paraphrases, and notes; quotes require the user's verification flag. Each answer contains attribution, context, a human-confirmed status, remaining gap, and whether documentary support exists. A commitment requires an explicit record that it was agreed. No automatic speech recognition, classification, or authenticity guarantee is provided.

## Records-request and follow-up drafts

```sh
flockoff red-tape --db work/accountability.sqlite --key work/accountability.key request demo-city-001 R01 --output work/request-001.txt
```

Request scopes include a period, categories, verified official channel metadata, fee ceiling, existing evidence, and a remaining question. An identical normalized scope in the same case is refused even if its editorial ID or fee ceiling differs. Submitted requests require an actual sent date and reference entered by the user. Use `--follow-up` only for an open submitted request. Nothing is submitted by this module.

The request log supports response evidence, renewal clauses, notice windows, responsible roles, corrections, chosen review dates, and verified legal-deadline metadata. A reminder becoming due never establishes a legal violation. No legal timetable is calculated automatically. Current local legal rules and meeting procedures must be checked separately.

## Review and export

Every generated file is a private draft. Inspect it and make a redacted candidate copy if needed. Private contact/notes fields are excluded from the packet projection; public-facing free text can still contain personal information entered by the user. Inspect source URLs, notes, answer attributions, and document excerpts as well as the brief.

```sh
flockoff red-tape --db work/accountability.sqlite --key work/accountability.key approve work/redacted-candidate.html --reviewer "Reviewer name" --attest-redactions-and-consent
flockoff red-tape --db work/accountability.sqlite --key work/accountability.key export work/redacted-candidate.html --output work/approved-public-copy.html
```

Approval binds exact file bytes. Any change requires new approval. Export is a local copy, never publication. An approval is a user attestation, not an identity signature or automated privacy certification. A redacted candidate will differ from the original packet; `verify-packet` verifies the original generated packet, while approved exports bind the independently reviewed candidate bytes.

## Input contract

See `examples/case.json`, `examples/answer.json`, and `src/flockoff_red_tape/model.py`. The validator rejects unknown fields, duplicate IDs, dangling references, cycles, unsupported statuses, missing assessment categories, and malformed dates. The CLI additionally rejects duplicate JSON keys, non-finite values, and JSON files larger than 8 MiB. Document attachment is limited to 20 MiB per file.

Source records hold issuer, dates, original URL, exact locator, excerpt/paraphrase, limits, optional license, parent lineage, supersession, and saved-document SHA-256. Five declared mirrors collapse to one root; identical document hashes collapse even if a parent edge was omitted. Undisclosed copying between different sources cannot be inferred automatically. Root count is not calibrated confidence or proof of independence.

Factual premises without support cannot reach ready status; unresolved open questions remain explicitly labeled. The reviewer is responsible for whether a cited source actually supports the wording and whether relevant counterevidence is complete. No model judges truth, ownership, surveillance purpose, compliance, or criminality.

## Storage and custody

The accountability SQLite database is separate from the RF evidence database. Full case snapshots, document bytes, and approval records use authenticated Fernet encryption. Random keys are generated at initialization and stored in a separate user-chosen file; POSIX output permissions default to 0600 and draft directories to 0700. These are not a substitute for a protected computer or disk encryption. File permissions differ on other operating systems and have only been tested on Linux.

Case IDs, revision numbers, keyed custody digests, and public-document/artifact digests remain visible as metadata. Use opaque case IDs. Encryption and custody HMAC keys are purpose-separated. Operational snapshot digests are keyed; public-document and reviewed-artifact digests use SHA-256. New files and packet directories never silently overwrite old ones.

Revision writes and associated document attachment occur in one SQLite transaction. SQL triggers reject ordinary updates/deletes. Authenticated ciphertext and HMAC chains detect modification and internal gaps. They do not prevent a database owner from dropping tables, deleting all data, restoring an earlier complete backup, or truncating the latest suffix. Keep external receipt checkpoints and protected backups if those threats matter. Losing the external key loses access; a co-stored or stolen key defeats confidentiality. Plaintext imports, editing copies, drafts, printouts, and public exports need their own retention decisions. No automatic deletion or retention scheduler is implemented in this version.

## FLOCK OFF integration boundary

The bundle is based on the exact v0.3.0 ZIP linked in the V1.0 GitHub release body, not the unrelated BLOOMCORE NOW tag source tree. The baseline archive SHA-256 is `84d816e9d2d2c67b1b0466afdd63bf7beab36b3d866fbbfc97cd849934a097d6`.

Host package version: `0.3.0+redtape.1`; companion version: `0.1.0`. This does not implement the v0.4 distributed-geometry milestone. The main CLI dispatches to the companion package only when `red-tape` is selected. Sensor, mobile-track, signature, geometry, and RF-ledger logic remain unchanged. Accountability records do not become RF node estimates or raw sensor attachments.

All new original code is Apache-2.0. The existing dependency and upstream license notices remain in effect. The URL parser is `urllib.parse`, a parser only; no URL is fetched by the runtime. No networking module, network service, active RF path, automatic sender, or telemetry client was added.

## Tests

```sh
PYTHONPATH=src python3 -m unittest discover -s TESTS -p 'test_*.py' -v
python3 tools/verify_release.py
```

The module tests exercise evidence closure, review invalidation, lineage/digest deduplication, immutable answers, encrypted document retention, stale writers, corruption, exact-byte approvals, HTML escaping, timing refusal, request deduplication, and packet reconstruction after later edits. Existing sensor/replay tests remain part of the same suite.

The original two Markdown specifications are retained under `specifications/`. This implementation uses explicit input and human-reviewed status; it does not implement automated research, extraction from PDFs, answer suggestion, or automatic question ranking. The user supplies question order with a written reason. It also does not provide a graphical case editor: the functional UI is the generated Town Hall view, and authoring uses CLI/JSON.
