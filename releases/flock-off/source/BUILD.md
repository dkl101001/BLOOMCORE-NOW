# Build and run

The sensor runtime retains replaceable receive-only adapter boundaries and performs
no native radio capture itself. The successor additionally contains explicitly
enabled collaboration and public-research transport boundaries. See
docs/COLLABORATION_PROTOCOL.md and requirements.lock. Neither starts network work
by default. The historical sensor commands below remain scoped to that runtime.

## Verified environment

- CPython 3.12.13
- Exact Windows runtime dependency versions and wheel hashes: requirements.lock
- SQLite from the CPython standard library

## Test without installing

From the package root:

```sh
PYTHONPATH=src python3 -m unittest discover -s TESTS -p 'test_*.py' -v
```

## Replay the deterministic synthetic trace

```sh
export FLOCKOFF_ROTATION_SECRET_HEX=000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f
export FLOCKOFF_ROUTE_KEY_BASE64=AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=
PYTHONPATH=src python3 -m flockoff.cli replay \
  --input TESTS/synthetic_traces/fixed_two_pass.jsonl \
  --signature SIGNATURES/candidate/flock_you_wifi_assertion_v0.1.0.json \
  --ledger /tmp/flockoff-ledger.sqlite \
  --output /tmp/flockoff-replay.json
```

The two secrets above are public deterministic test vectors and must never be used
for field observations. The JSON output omits plaintext poses; the SQLite route
vault contains only authenticated ciphertext for them. Field launch must obtain
separate rotation and route-encryption keys from a platform keystore. The sensor runtime can consume an external receive-only Flock-You USB/NDJSON stream; it still performs no native radio capture. Networking is confined to the successor's explicit collaboration/public-research modules.

## Live v0.2 smoke test

Use `flockoff live-flock-you` with an external receive-only Flock-You NDJSON source and a separate local pose NDJSON source. Real field secrets are mandatory. See `docs/LIVE_REALITY_LOOP.md`.

## Live v0.3 Remote ID smoke test

Use `flockoff live-remote-id` with an external decoded receive-only Remote ID
NDJSON source and a separate local pose source. The checked-in synthetic streams
exercise the host loop only; they do not validate a radio or transport. See
`docs/LIVE_REMOTE_ID.md`.
