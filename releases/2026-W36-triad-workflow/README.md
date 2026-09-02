<!-- SPDX-License-Identifier: Apache-2.0 -->

# BLOOMCORE Triad-Derived Workflow v0.1.0

> Preserve the source. Bound the claim. Prove the work.

State: **Φ — RELEASE_CANDIDATE_NOT_SHIPPED**

This small, dependency-free Python tool turns a source-bound task packet into
a deterministic workflow report and receipt. It preserves the Triad's three
different roles without exposing or pretending to execute the private system.

## One-minute demo

From this release directory:

```bash
export PYTHONPATH="$PWD/packages"
python -m triad_workflow validate examples/source-bound-workflow/workflow.json
python -m triad_workflow run examples/source-bound-workflow/workflow.json --out /tmp/triad-workflow-run
python -m triad_workflow verify /tmp/triad-workflow-run
python -m triad_workflow replay examples/source-bound-workflow/workflow.json /tmp/triad-workflow-run
```

The synthetic fixture demonstrates stale-binding inspection without publishing
private source material. Choose a fresh output path for each run; `run` refuses
to overwrite an existing path.

## What it enforces

- exactly three role-bound sources: master, bounded DSK companion, adapter;
- explicit SHA-256 identity rather than filename authority;
- five epistemic claim classes without automatic uplift;
- eight explicit execution-profile axes;
- contradiction text, rejected interpretations and unresolved remainder;
- evidence-bound completion and a single bounded claim;
- closed mutation, promotion, and external-action permissions;
- deterministic artifacts, tamper checking and byte-for-byte replay.

## What it does not claim

The tool is a `DERIVED_NONAUTHORITATIVE` structural witness. It is not native
MANTIS, MIRRORSEED, ECA, Phase 151 embodiment, scientific validation, semantic
truth, canonical promotion, or organism-wide reachability. It does not mutate
sources, use the network, run arbitrary commands, or activate a release.

See [the workflow specification](docs/WORKFLOW_SPEC.md), [boundary and
limitations](docs/BOUNDARY_AND_LIMITATIONS.md), and [threat model](docs/THREAT_MODEL.md).

## Test

```bash
python -m unittest discover -s tests -v
```

Python 3.11–3.13 is supported using the standard library at runtime.

## License map

The CLI package and tests are MPL-2.0. Contracts, docs, examples, templates,
release metadata, and evidence are Apache-2.0. See `LICENSE_MAP.md` and `NOTICE`.
