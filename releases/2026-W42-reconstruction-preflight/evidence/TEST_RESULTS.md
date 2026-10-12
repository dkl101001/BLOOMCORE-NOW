<!-- SPDX-License-Identifier: Apache-2.0 -->

# Test and experiment results

- Environment: Python 3.12.14; Linux 6.18.44 x86_64
- Runtime dependencies: standard library only
- Unit/integration/adversarial tests: `19/19 PASS`
- Repeat under `PYTHONHASHSEED=314159`: `19/19 PASS`
- Install/import/CLI smoke test: `PASS` using isolated `--target`
- Experiment: `8/8 PASS`, result `SUPPORTED_WITHIN_BOUNDS`
- Six-dimension false allows: `0`
- Deliberately weak hash-only baseline false allows: `6`
- Example receipt verification: `PASS`

## Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src \
  python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=314159 PYTHONPATH=src \
  python -m unittest discover -s tests -q
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=random PYTHONPATH=src python experiment.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m reconstruction_preflight \
  validate examples/verified.json --receipt evidence/example-receipt.json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m reconstruction_preflight \
  verify-receipt evidence/example-receipt.json
```

## Evidence hashes

- `evidence/example-receipt.json`: `8bf53a07ca65e364e6fc6af8501b2e2da00caf3ba90f94f507e801c67bcce2e8`
- `evidence/experiment-results.json`: `3d8be8c1527aa147cc33edf7b90de7c36c45cfc25acd0e35f666b6f7b2a99ecf`
- Experiment internal receipt hash: `97df4e89c34596e083830b4671b40d95d5258577f34ffa5209484fa8b4f677a1`

## Negative and inconclusive results

- A clean virtual environment created by the host did not contain `setuptools`, so an offline isolated wheel build could not start there. The same package successfully built, installed to an isolated target, imported, and exposed its CLI using the host build backend. This is an environment-bootstrap limitation, not evidence of cross-platform installability.
- External replay, non-Linux platforms, symlink race testing, remote signature verification, and production-repository aggregate checks were not run.
- No claim beyond synthetic structural behavior is supported.

