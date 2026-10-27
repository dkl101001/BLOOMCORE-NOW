<!-- SPDX-License-Identifier: Apache-2.0 -->
# Owner-selected document variants

The isolated `VariantStore` generates UTF-8 text variants before preview, digest and approval. Supported categories are meeting preparation, records request drafts and personal records. Every variant receives a neutral category-accurate title and a cryptographically random reference. Exclusive file creation detects collisions.

The caller supplies already-selected text and a separate private source reference. The module does not read cases, rooms or collaborators. Caller-provided text must be reviewed for identity and sensitive content; selecting unbranded output removes only generated product branding, not words already present in the selected text. Required participant/nonofficial, human-verification and non-anonymity disclosures remain.

`create(...)` returns an immutable `Preview` containing exact bytes and SHA-256. Show these bytes to the user. `approve(reference, preview.sha256, reviewer=..., consent=True)` records approval for that exact variant. `export(reference, preview.sha256, output)` copies those bytes locally; it never prints, sends or publishes. A new variant requires new approval. Reprinting an approved variant preserves identical bytes.

`VariantStore(private_directory, external_fernet_key)` encrypts the private mapping, rendered bytes and reviewer approval. `recover_source(reference)` recovers the private source mapping; it is never embedded automatically in output. Preserve the external key separately. Local metadata still exposes opaque filenames and file sizes. Renaming does not make documents anonymous or unlinkable.

Optional presenter text requires `disclose_presenter=True`, is part of the preview and digest, and comes only from the caller's explicitly selected presenter field. No collaborator names are looked up or inferred. This module is an integration API; it does not by itself add desktop controls or claim complete council/share UX.
