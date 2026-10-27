# Validation and release boundary

Build: FLOCK OFF `0.3.0+redtape.1`, companion module `0.1.0`.

Baseline: `FLOCK_OFF_CLEAN_REPO_v0.3.0.zip`, SHA-256 `84d816e9d2d2c67b1b0466afdd63bf7beab36b3d866fbbfc97cd849934a097d6`, retrieved from the v0.3.0 attachment linked in the body of https://github.com/dkl101001/BLOOMCORE-NOW/releases/tag/V1.0. The release tag's Git tree is BLOOMCORE NOW and is not the baseline used here. No repository push or release publication was performed.

Verification target: Linux, Python 3.12.14, cryptography 46.0.0, cffi 1.17.1, pycparser 2.23. The dependency versions are those in the original requirements lock. The environment's cryptography 50.0.2 also passed the suite during development; that is not the release dependency pin.

Validation performed:

- 68 baseline tests passed before integration.
- Integrated suite: 116 tests, comprising those 68 baseline tests and 48 companion tests.
- Installed-wheel commands were exercised from outside the source directory: initialize, import, review, dispense, reconstruct packet, draft records request, approve, export, and original RF replay.
- New runtime Python was included in the no-network-import audit. The only URL-related import is `urllib.parse`, used for validation, with no fetch operation.
- Existing RF, live Remote ID, geometry, signature, and evidence-ledger implementation files were compared byte-for-byte with the recovered baseline. Changes to the existing package are the CLI dispatch, version metadata, documentation/notices, and release tooling.
- New source ZIPs were built twice and compared; final artifact checksums are reported by the release build tool. Each ZIP contains a root README and embedded source manifest.
- The final ZIP was extracted separately, its manifest verified, and the integrated tests rerun from the extraction.

Town Hall UI boundary: HTML escaping is regression-tested. The inline script hash was checked against the Content Security Policy, and start/tick/pause/reset/print logic passed in an isolated JavaScript DOM stub. Chromium was unavailable and its attempted download failed. Browser rendering, real browser timer/CSP behavior, accessibility with assistive technology, and physical one-page print fit have not been visually verified in this environment. The sample packet is explicitly fictional and its displayed sample receipt is not a live custody receipt.

Operational boundaries: no real council packet, jurisdiction-specific deadline, actual official response, or live public-record submission was verified. Human review assesses source support, counterevidence, redactions, consent, and local rules. Quotation verification flags are user attestations, not automated authentication. No sensor field-validation claims are added by this module.

The original two specifications are under `specifications/`. Automated research, PDF extraction, AI ranking/status suggestion, graphical case authoring, automatic retention deletion, and public sending/publication remain outside this implementation. Case authoring and editing use validated JSON and CLI; the Town Hall presentation is functional offline HTML. See the module README for the complete storage and threat limits.

## Authorship correction

The build now explicitly credits Frazer Σ Love ACO-Σ and Sara ΣΩ as co-authors in AUTHORS.md, NOTICE, project metadata, both runtime package metadata surfaces, and the root/module READMEs. Upstream attribution and archived specification wording remain preserved. The example packet source digest and release manifest were regenerated for the corrected source bytes.
