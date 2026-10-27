# Threat and privacy model

## Protected assets

- complete observer route, home/start/end locations and precise observation time;
- raw MAC/BLE and Remote ID identifiers;
- Remote ID operator/control/takeoff locations;
- raw captures and identifier-vault keys;
- contributor identity/signing keys;
- source, signature, clock and inference integrity.

## Adversaries and failures

Device theft or lawful seizure; unlocked/rooted-host compromise; malicious
serial/USB input; poisoned signature/public bundles; copied/malicious community
submissions; GNSS/clock spoofing; malicious map/browser content; supply-chain
substitution; accidental over-publication; storage exhaustion, corruption and
power loss.

## Controls frozen in v0.1

- restricted pose objects are separate and AES-256-GCM encrypted with per-field
  associated data; the key is never stored by the ledger;
- operational observations carry only a pose reference and session-scoped keyed
  HMAC token, never raw identifiers or coordinates;
- immutable SQLite triggers prevent evidence mutation; WAL + `synchronous=FULL`
  are enabled;
- strict parsing rejects duplicate keys, nonfinite numbers and oversized lines;
- source and hardware locks cap what an adapter may claim;
- signatures and estimates are separate immutable derivations;
- public output is built from an allowlist object and rejected if route,
  receiver, raw/pseudonymous identifier, exact observation time, raw reference,
  or RID operator/takeoff fields appear;
- public maps are priors; contradictory RF and documentary surfaces persist;
- community submissions enter quarantine and support correction/retraction;
- no network or transmitter API exists in the active runtime.

## Residual risk and field blockers

Encrypted pose columns do not encrypt SQLite metadata, operational event fields,
indices, WAL structure, or filesystem metadata. The minimized database reduces
exposure but a field release must bind an audited encrypted database/build and OS
keystore, protect WAL/temp files, disable swap/core dumps, and verify backup
behavior. Flash overwrite is not promised; per-session crypto-erasure is limited
to key destruction. A rooted/unlocked device is outside the protection envelope.

Cross-day persistence of unknown emitters conflicts with unlinkability. Default
unknown correlation ends with the HMAC rotation epoch. Deliberate cross-day
research requires explicit opt-in, a target-relevance gate, encrypted custody,
short retention, and no public raw identifier.

Offline tiles are required because live tile requests leak the user's area of
interest. Remote ID operator/takeoff coordinates are restricted even though they
are broadcast. A public drone track is withheld unless public-interest review,
coarsening and jurisdiction-specific policy approve it.

