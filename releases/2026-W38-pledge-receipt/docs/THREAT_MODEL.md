<!-- SPDX-License-Identifier: Apache-2.0 -->

# Threat model

## In scope

- ambiguous JSON through duplicate keys or non-finite numbers;
- output overwrite and accidental evidence destruction;
- packet/source mismatch when source bytes are provided;
- receipt tampering after generation;
- silent loss of a stable commitment ID or populated field;
- heuristic extraction presented as semantic understanding.

## Controls

- strict UTF-8 JSON parsing rejects duplicate keys and non-finite numbers;
- output is no-clobber by default;
- optional source-byte hashing checks correspondence;
- receipts are canonicalized and self-hashed;
- scaffolding leaves semantic fields `null`;
- diff signals are labeled structural and nonauthoritative.

## Out of scope

Malicious source documents are treated as inert text; the program executes no
document content and performs no network access. It does not validate digital
signatures, legal authority, policy truth, implementation evidence or human
interpretation. Resource-exhaustion limits and streaming input remain future
hardening work.
