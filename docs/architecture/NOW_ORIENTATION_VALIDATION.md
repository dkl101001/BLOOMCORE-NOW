<!-- SPDX-License-Identifier: Apache-2.0 -->

# NOW orientation wave — validation record

Date: 2026-09-14. Documentation-only successor to main `791f599` (the repository state inspected for this wave). Current source scope is recorded in [Hybrid reference map](HYBRID_NOW_REFERENCE.md).

## Change boundary

Updated root entry guidance; added a NOW-specific FAQ and current Hybrid source/evidence map; added historical-context notices to the earlier FAQ, technical FAQ, source matrix and v1.5 orientation. Refreshed the root observational package receipt from staged Git bytes. No runtime, release directory, EDP frozen instrument, CI definition, tag, release approval or component license was changed. W37 and W38 draft development remains separate. Basics was not modified.

## Fresh checks

Windows Python 3.13, isolated environment with NumPy 2.5.3 and jsonschema 4.26.0:

- Initial existing checkout: W31's 11 tests and W35's five tests passed; W36 failed on synthetic-source hash mismatches and stopped the aggregate runner. This failure is retained, not converted into a pass.
- A fresh local clone with `core.autocrlf=false`, overlaid with the documentation changes, passed **95 tests**: W31 11, W35 five, W36 17, EDP-01 31, EDP-02 31. License and public-boundary checks passed.
- The byte-preserving checkout also completed W36 validate, run, verify and byte-for-byte replay on the supplied synthetic example, writing a fresh local output directory.
- Changed Markdown local file links were checked for target existence. No claim of full external-URL or heading-anchor validation.
- Release directories, EDP-01, EDP-02, tooling and CI definitions have no diff from the inspected base. Neither model trials nor training were run; EDP test fixtures do not establish research hypotheses.

## Windows custody finding

Git line-ending conversion in the original working checkout changed source bytes relative to W36's expected hashes. Its original fixture records were not rewritten. The [NOW run guide](../faq/NOW_FAQ.md) provides a new-checkout procedure with conversion disabled instead of instructing users to overwrite existing work or change expected hashes. A repository-wide attributes migration could be considered separately after a custody review; it is not hidden in this documentation change.

## Remaining limits

This is a bounded documentation and usability pass, not a full canonical source read, native integration audit, experimental model trial, new release approval, or guarantee of every supported platform. Only Windows Python 3.13 was run locally here. CI's Python 3.11/3.12/3.13 results must be observed separately after publication. The root receipt verifies indexed content only; it grants no semantic or publication authority.
