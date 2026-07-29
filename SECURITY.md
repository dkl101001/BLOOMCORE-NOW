<!-- SPDX-License-Identifier: Apache-2.0 -->

# Security

Do not open a public issue for a vulnerability that could expose private data,
execute arbitrary code, bypass a release boundary, or enable unsafe network
fetching.

Until a dedicated private reporting channel is published, provide only a
minimal non-operational notice to the maintainers and do not include exploit
payloads in public discussion.

Week One fetches only explicit `http` and `https` citation targets, rejects
embedded credentials, blocks local and private network destinations, limits
response size, and does not execute downloaded content.

