<!-- SPDX-License-Identifier: Apache-2.0 -->

# Workflow specification

The Triad-derived workflow turns a bounded task packet into a replayable
structural witness. It does not import the private Triad corpus or claim to run
the BLOOMCORE organism.

## Processing sequence

1. Parse strict JSON, rejecting duplicate keys and non-finite numbers.
2. Bind exactly three differentiated roles to content hashes.
3. Limit the DSK companion to the named Phase 38 §33.17 aperture.
4. Validate all five epistemic classes and all eight execution-profile axes.
5. Preserve contradiction text, exact source references, rejected readings and
   unresolved remainder.
6. Require each acceptance criterion to have exactly one state and evidence
   before a bounded completion claim is allowed.
7. Emit a canonical source manifest, readable report and self-hashed receipt.
8. Verify artifact hashes or replay the input byte-for-byte.

The eight axes are `transition`, `recursion`, `exploration`, `scheduling`,
`replay`, `persistence`, `mutation`, and `authority`. An upstream sentence says
“all seven axes” while enumerating eight. This derivative follows the explicit
eight-item enumeration and records the wording mismatch without altering canon.

## Commands

```bash
triad-workflow validate workflow.json
triad-workflow run workflow.json --out run
triad-workflow verify run
triad-workflow replay workflow.json run
```

`run` refuses to use an existing output path. The program reads bound sources
but never changes them and has no network or arbitrary command-execution path.
