<!-- SPDX-License-Identifier: Apache-2.0 -->

# BLOOMCORE NOW — current FAQ and run guide

Public derived guidance, 2026-09-14. This page describes NOW specifically. It is not a canonical amendment, a change to a frozen instrument, or a claim of native organism execution. See the [source/evidence map](../architecture/HYBRID_NOW_REFERENCE.md).

## What should I use this repository for?

Use NOW for bounded applications, inspectable workflow tools and experimental research instruments. It is the active applied-build focus. Basics remains preserved adoption lineage; BLOOMCORE Public carries broader architecture and release ancestry. Shared design does not make every repository's wording or runtime identical.

## What does Hybrid Triad mean here?

The Operator selected the Hybrid Triad as the current working reference. It carries the constitutional spine, execution-selection law and build contracts with embedded Keystone science. Its own full-master binding remains intact. A public summary, adapter or hash does not replace the selected source, and a source's canonical status does not prove that its runtime exists.

Within that reference, BLOOMCORE is field and organism; OI means Organismal Intelligence, not Organic or Organoid Intelligence. OI is a paradigm, not another module to import. H1–H7 remain hypotheses. We preserve differentiated identity, source lineage, declared boundaries, and the distinction between evidence and authority.

## Which existing tools can I try?

| Surface | What it does | What it does not establish |
|---|---|---|
| [W36 Triad-Derived Workflow](../../releases/2026-W36-triad-workflow/README.md) | Validates a source-bound packet and emits/verifies/replays structural evidence | Semantic truth, native MANTIS/MIRRORSEED, or organism-wide execution |
| [W35 Panic Professionally](../../releases/2026-W35-panic-professionally/README.md) | Local incident timeline, SQLite state, ownership and evidence exports | Native organism memory or identity continuity |
| [W31 BLOOMCORE RECEIPT](../../releases/2026-W31-bloomcore-receipt/README.md) | Source-surface inspection and evidence receipts | Truth certification; optional URL checks are network activity |
| [EDP-01](../../EDP-01/README.md) | Frozen experimental protocol and blinded scoring/provenance tooling | Completed model trials or confirmed hypotheses |
| [EDP-02](../../EDP-02/README.md) | Frozen architectural-causality and longitudinal experiment tooling | Completed training/model trials or proof of endogenous agency |

Read each module's own requirements and limitations. EDP-01 and EDP-02 report `MODEL_TRIALS_NOT_RUN`. Publication approval and synthetic test fixtures do not change that status. This documentation update does not run models, register a new experiment, or alter frozen instruments.

## How do I run the current workflow on Windows?

Use Python 3.11–3.13 and a byte-preserving checkout. On Windows, use a **new directory** so Git does not convert frozen fixture line endings:

```powershell
git -c core.autocrlf=false clone https://github.com/dkl101001/BLOOMCORE-NOW.git BLOOMCORE-NOW-byte-exact
Set-Location BLOOMCORE-NOW-byte-exact
```

This does not repair or overwrite another checkout. If an existing checkout reports a synthetic-source hash mismatch, do not rewrite the expected hash or frozen fixture to make it pass. A CRLF-converted Windows checkout failed during this documentation pass; a fresh checkout with conversion disabled passed. From that new repository root:

```powershell
Set-Location releases/2026-W36-triad-workflow
$env:PYTHONPATH = (Resolve-Path packages).Path
$demoRun = Join-Path ([IO.Path]::GetTempPath()) ('bloomcore-now-' + [guid]::NewGuid().ToString('N'))
python -m triad_workflow validate examples/source-bound-workflow/workflow.json
python -m triad_workflow run examples/source-bound-workflow/workflow.json --out $demoRun
python -m triad_workflow verify $demoRun
python -m triad_workflow replay examples/source-bound-workflow/workflow.json $demoRun
```

Each run uses a fresh output path; the tool refuses to overwrite an existing run. Keep the directory if you want to inspect its evidence. Linux/macOS instructions remain in the [release README](../../releases/2026-W36-triad-workflow/README.md).

## How do I check the repository?

From the root, in an isolated Python environment:

```text
python -m pip install -r EDP-01/requirements.txt -r EDP-02/requirements.txt
python forge_tools/run_all_tests.py
```

The aggregate runner discovers weekly release suites and both EDP suites, then runs license and public-boundary checks. The repository CI declares Python 3.11, 3.12 and 3.13 jobs. A local run proves only its recorded environment; it is not evidence those CI jobs passed. Root pytest discovery is not a substitute for this aggregate command.

## Does this need JAX or a language model?

The W36 structural workflow is standard-library Python. The EDP tools require NumPy and jsonschema, and real model collection requires separately supplied adapters and registered inputs. Do not install or enable a model merely to produce structural receipts. No model call is not the same claim as a functioning model-zero native organism.

## What must stay separate as NOW develops?

Receipts witness; metrics measure bounded behavior; models propose or render; native mutation requires its actual authorized pathway. An audit output must not silently become a native pause, clamp or admission gate. Current execution declarations distinguish transition, recursion, exploration, scheduling, replay, persistence, mutation and authority. A runnable utility alone does not satisfy every native integration obligation.

## Do we replace old releases with Hybrid versions?

No. Preserve original tags, source bytes, receipts, names and open failures. A successor gets explicit source bindings and evidence for its own behavior. Complete current portable deliverables carry their needed dependencies and reference external ancestry rather than recursively embedding every older release. Missing ancestry must be named, not silently presented as verified reconstruction.

## Where are licensing and earlier architecture explanations?

Use the [repository license map](../../LICENSE.md) and nearest component notices; this is not an interchangeable choice among three licenses. Earlier [general FAQ](FAQ.md), [technical FAQ](FAQ_TECHNICAL.md), and [Phase 38 orientation](../architecture/PHASE_38_PUBLIC_ORIENTATION.md) remain dated lineage. Their inherited source labels are not automatic current-runtime certification.
