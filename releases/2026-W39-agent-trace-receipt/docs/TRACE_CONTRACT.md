<!-- SPDX-License-Identifier: Apache-2.0 -->

# Trace contract

The policy is strict JSON. It names one run, one expected actor, six complete
allowlists, and how unknown event kinds should be handled. The trace is JSONL,
one event per line:

```json
{"seq":1,"actor":"coding-agent","kind":"file_write","target":"src/app.py"}
```

Supported kinds are `file_read`, `file_write`, `file_delete`, `command`,
`network_host`, and `tool`. File targets must be relative and cannot contain
`..`. Network targets are hostnames without a scheme, port, or path.

Patterns use case-sensitive shell wildcards. A network pattern such as
`*.example.com` matches subdomains but not the apex. An empty allowlist denies
all supplied events of that kind. Unknown kinds remain `UNKNOWN` unless the
policy explicitly sets `unknown_kinds` to `VIOLATION`.

The receipt preserves input order and source line. It does not reorder or
deduplicate events because repetition can be consequential evidence.

