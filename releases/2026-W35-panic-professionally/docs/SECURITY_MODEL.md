<!-- SPDX-License-Identifier: Apache-2.0 -->

# Security and Evidence Model

## Local boundary

The CLI performs no network requests and collects no telemetry. The dashboard
binds to `127.0.0.1` by default and exposes read-only incident data from the
selected SQLite file.

Do not bind the dashboard to a public interface without adding authentication,
transport security and an explicit deployment threat model. Incident records
often contain operationally sensitive information.

## Receipt claim

Each event receipt hashes a canonical event payload together with the previous
event's receipt hash. Verification can detect modification, deletion,
reordering or chain substitution within the observed database history.

A valid chain proves only internal consistency of the preserved event sequence.
It does not prove that an event was truthful, complete, timely or written by the
person named as actor. The SQLite database is not a hardened append-only store.

## Deliberate exclusions

- no credentials, secrets or production-system access;
- no remote paging, messaging or webhook execution;
- no authentication or multi-user authorization layer;
- no protected BLOOMCORE identity, memory or orchestration surfaces.
