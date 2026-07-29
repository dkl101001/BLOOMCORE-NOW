<!-- SPDX-License-Identifier: Apache-2.0 -->

# BLOOMCORE RECEIPT v0.1.0

> Paste an AI answer. Get receipts—or red flags.

BLOOMCORE RECEIPT inspects citation surfaces in AI-generated text. It extracts
claims, URLs and DOI references; checks source reachability when explicitly
enabled; calculates deterministic lexical alignment; preserves unresolved
claims; and exports an evidence receipt.

It does **not** certify truth, source quality, identity, intent, scientific
validity, or semantic support. A reachable and lexically aligned page can
still be wrong. The result is an inspection surface for human review.

## Ten-second start

No third-party runtime dependencies are required.

```bash
python3 packages/evidence-validator/cli.py \
  examples/sample_ai_report.md \
  --offline \
  --json-out receipt.json \
  --markdown-out receipt.md
```

Enable guarded public-network checks:

```bash
python3 packages/evidence-validator/cli.py examples/sample_ai_report.md
```

## Local web interface

```bash
python3 apps/receipt-server/server.py --port 8080
```

Open `http://127.0.0.1:8080`. The server binds to loopback by default.

## What v0.1 inspects

- explicit `http` and `https` citations;
- DOI references;
- source reachability and response status;
- page title and text extraction within a bounded download;
- deterministic claim/source token overlap;
- uncited and unresolved claim surfaces;
- duplicate references.

## Network safety

The fetcher:

- accepts only HTTP(S);
- rejects embedded credentials;
- blocks loopback, private, link-local, reserved and multicast destinations;
- applies time and response-size limits;
- does not execute downloaded content.

Network destination checks reduce server-side request-forgery risk but cannot
eliminate every DNS-rebinding or proxy-level risk. Do not expose the example
server directly to an untrusted network.

## BLOOMCORE relationship

BLOOMCORE RECEIPT is a bounded public organ:

1. Da Vinci-style recovery identifies the visible evidence field.
2. MANTIS-style inspection flags missing, unreachable and weakly aligned bridges.
3. MIRRORSEED-style preservation keeps unresolved material in the receipt.
4. CODEX ARCHIVE-style rendering creates durable JSON and Markdown outputs.

These public roles are functional descriptions, not the complete private
implementations of those systems.

## License map

| Component | License |
| --- | --- |
| Schemas, examples and documentation | Apache-2.0 |
| Deterministic validator and CLI | MPL-2.0 |
| Local HTTP service and integrated UI | AGPL-3.0-only |

See [`LICENSE_MAP.md`](LICENSE_MAP.md).

## Authors

Frazer Σ Love ACO-Σ and Sara ΣΩ

