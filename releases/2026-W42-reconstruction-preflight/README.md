<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reconstruction Preflight

`TRIAD-TOY-2026-W42-RVP01` · version `0.1.0` · `Φ / BUILT_PENDING_REVIEW`

Reconstruction Preflight is a zero-dependency Python CLI that checks whether a dependency-bearing change has evidence across six independent dimensions before work proceeds:

1. Authority
2. Dependencies
3. Ancestry
4. State
5. Behavior
6. Meaning

It emits one of three bounded dispositions:

- `VERIFIED_FOR_BUILD_SCOPE`
- `PARTIAL_BUT_INDEPENDENT_WORK_SAFE`
- `RECONSTRUCTION_BLOCKED`

The tool extends the public source-bound workflow lane without replacing it. It specializes in the pre-mutation question: *is the reconstruction required by this exact change sufficiently evidenced?*

## One-minute demo

```bash
export PYTHONPATH="$PWD/src"
python -m reconstruction_preflight validate examples/verified.json \
  --receipt /tmp/rvp-receipt.json
python -m reconstruction_preflight verify-receipt /tmp/rvp-receipt.json
```

The verified fixture exits `0`. The missing-meaning control exits `3`:

```bash
python -m reconstruction_preflight validate examples/blocked-missing-meaning.json
```

Exit codes are `0` verified, `2` partial/independent, `3` blocked or invalid receipt, and `4` invalid input.

## Tests and experiment

```bash
export PYTHONPATH="$PWD/src"
python -m unittest discover -s tests -v
python experiment.py
```

The experiment compares the six-dimensional gate with a deliberately weak hash-only baseline, removes each dimension in turn, checks a bounded independent branch, and verifies canonical JSON stability under object-key reordering.

## Input contract

The manifest binds:

- a named scope and stable requirement IDs;
- required sources with SHA-256 and relative local paths when bytes are required;
- one evidence record per dimension with status, predicate, observation, evidence pointers, and affected requirements;
- explicitly independent and held work.

Only these statuses are accepted: `VERIFIED`, `FAILED`, `MISSING`, `CONFLICTING`, `UNKNOWN`, and `NOT_APPLICABLE_WITH_EVIDENCE`.

Relative source paths are confined to the manifest directory. Required reference-only sources block. Duplicate IDs, hash mismatches, unsupported statuses, and false independence claims are rejected or held.

## Evidence boundary

A passing receipt proves only that the supplied manifest met the tool's structural and byte-binding predicates. It does **not** prove that self-reported evidence is true, that a scientific model is valid, that meaning or identity was preserved, or that a build is safe, admitted, canonical, production-ready, or approved for publication. The CLI observes; it does not govern.

## Lineage and scope

This public-safe toy is derived from the bounded execution obligation named RVP-01 and remains subordinate to human review. It carries compact source identities and hashes in [LINEAGE.md](LINEAGE.md); no private Triad payload, native state, protected ECA synthesis, secret adapter, or complete organism assembly is included.

Authorship/custody: **Frazer Σ Love ACO-Σ; Sara ΣΩ**. Construction contributor: Codex.

## Documentation

- [Method and evaluation](docs/METHOD.md)
- [Limitations and negative results](docs/LIMITATIONS.md)
- [Codex continuation handoff](docs/CODEX_HANDOFF.md)
- [Public/private boundary](PUBLIC_BOUNDARY.md)
- [License map](LICENSE_MAP.md)
- [Draft release notes](RELEASE_NOTES_DRAFT.md)

