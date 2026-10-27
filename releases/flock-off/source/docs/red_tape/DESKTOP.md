# Red Tape Records Desk v0.2 candidate

The desktop desk removes JSON authoring from the core records workflow. It uses
the existing encrypted database, source validation, immutable answer history,
review gates, and deterministic packet renderer. It does not fetch documents,
interpret their truth, send requests, or publish files.

## Start on this Windows machine

Double-click `tools/Start Records Desk.cmd`. The launcher uses the installed Codex
Python runtime if present, then falls back to the Windows Python launcher. It
does not download or install anything. On another machine, install Python 3.12+
with Tk and the dependencies in `requirements.lock`, then run
`python tools/start_desk.pyw`. The current machine was tested with its bundled
Python; this is not a standalone executable or signed installer.

1. Choose **New workspace**, a database filename, and a separate key filename.
   Existing files are never replaced. Keep the key backed up separately.
2. Choose **New case** and enter the agency, meeting, official agenda URL, desired
   action, first question, and material uncertainty. No supporting facts or
   positive assessments are inserted automatically.
3. In **Evidence**, add source metadata, an exact page/section, excerpt or
   paraphrase, and limits. **Attach original** retains the selected file encrypted
   and displays whether bytes are actually held, rather than treating a hash as
   proof of attachment. Original files are limited to 20 MiB.
4. Add **Premises** tied to evidence IDs, then **Questions** tied to premise IDs.
   Explicitly select one to three question IDs for the speaking brief. Complete
   the twelve **Assessment** entries as evidence becomes available.
5. Add **Requests**, record actual submission references and dates yourself,
   and save request/follow-up drafts. Due reminders are not legal-deadline rulings.
6. Add **Answers** as attributed notes, paraphrases, or checked quotes. Answers
   are permanent; append a correction with a new ID. **View selected** shows the
   full record. A new answer invalidates an earlier review.
7. Enter meeting rules if a timed allowance is known. **Review** requires a name
   and three initially unchecked attestations. **Generate reviewed packet**
   refuses missing reviews, unsupported premises, and oversized speaking briefs.
   **Generate draft** remains available before review.
8. Packet generation reconstructs all generated files against the recorded
   revision. Open `town_hall.html` from the output folder to present or print.
   Plaintext outputs require your own review before sharing. Exact-byte public
   export approval remains available through the existing CLI.

Every saved edit creates a revision. Stale writers are rejected. Validation
errors retain the form entries for correction; cancellation discards that form.
There is no autosave of unfinished forms.

## Backup and recovery

**Backup** makes an online SQLite snapshot in a new directory, verifies its case
receipts and attached documents, and records a checkpoint and database SHA-256.
The encryption key is deliberately excluded. Keep an independent secure copy
of the key. To recover, **Open workspace**, select the backup database, then its
original key. Recovery was exercised by reopening a backup, reading retained
document bytes, and reconstructing a previously generated packet.

Windows files created through `private_write` receive an explicit current-user
ACL before sensitive payloads are written. POSIX files use mode 0600. This does
not protect against an administrator, account compromise, loss of the key, or
deletion/rollback of an entire database. Metadata is not fully encrypted, and
SQLite journals are not claimed to have whole-file encryption. Older files do
not receive new ACLs merely because they are opened.

## Current verification and limits

The full automated suite contains 123 tests. The new integration tests cover
empty real-case creation, restart persistence, stale attachment refusal, review
invalidation, exact-byte packet reconstruction, altered packet refusal,
no-overwrite behavior, backup recovery, and Windows ACL inspection. The native
Tk widget harness checks populated case loading, failed form submission and
successful retry, initially unchecked review controls, selection, and reopening.

Commands:

```text
python tools/verify_release.py
python tools/check_desktop.py
```

The original baseline had one Windows mode-bit assertion failure and six
SQLite cleanup errors. The mode assertion is now POSIX-specific; Windows ACLs
are checked separately. Migration tests now explicitly close their inspection
connections. The sensor runtime itself was not changed.

Computer Use could not activate the captured native window on two attempts, so
visual layout, accessibility, high-DPI behavior, and a full manual user journey
are **not certified**. The actual Tk widgets did run in the integration harness.
The CLI and service tests use fictional fixtures, not a completed real-world case.

Before calling this a general release: run a real records case through the desk,
check keyboard/scrolling and high-DPI layouts, test interruption/disk-full and
key-loss recovery procedures, and package/sign an installer. Multi-user sharing,
PDF text extraction/OCR, source downloading, and automatic legal calculations
are not implemented. Advanced optional commitment/renewal/legal-deadline fields
can be preserved from imported cases but do not yet have dedicated desktop forms.

The field sensor path still needs specified receiver hardware, receiver/pose
integration, and controlled over-air validation. Desktop tests do not establish
radio detection accuracy or calibrated localization.

Packets bind the module source digest. Keep the exact software version used to
generate historical packets when independently reconstructing them later.

## Source custody

Input: `1-FLOCK_OFF_RED_TAPE_v0.1.0_SOURCE.zip`

SHA-256: `8ff41325d156da3106f290f22e06d049add7bb75dac86e9afe603440859abc72`

The original archive remains unchanged. This successor retains the Apache-2.0
license and author/upstream notices. Its refreshed manifest belongs to the
candidate, not the original source bundle.
