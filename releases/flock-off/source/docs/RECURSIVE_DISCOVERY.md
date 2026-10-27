# Recursive Discovery Constitution — v0.1.1

FLOCK OFF treats a blind spot as developmental pressure. A detector miss is not
an absence claim and `UNKNOWN` is not a terminal runtime outcome.

```text
DETECT
  ├─ match ─► CLASSIFY ─► LOCALIZE ─► RECEIPT
  └─ miss  ─► FAILURE_PACKET ─► ASSUMPTION_AUDIT ─► DISCOVER
                                      │
                                      ▼
                                NEXT_TEST_QUEUE
                                      │
                                      ▼
                         CANDIDATE_SIGNATURE
                                      │
                         NEGATIVE_CONTROLS
                                      │
                            REPLICATION
                                      │
                               VALIDATE
                                      │
                                      └────────► DETECT

KNOWN SIGNATURE ─► bounded mismatch ─► DRIFT
                                    ├─ insufficient coverage ─► RETEST
                                    └─ replicated drift ─► DEGRADE ─► DISCOVER
```

## Runtime invariant

Every unresolved discovery revision carries a non-empty `next_tests` list.
`VALIDATED` is reachable only through candidate, control-testing and replication
states. `SENSING_APERTURE_INSUFFICIENT` and
`NO_PRACTICALLY_SEPARABLE_PASSIVE_SIGNATURE_YET` are aperture states, not claims
that a target is radio-silent.

## Negative inference

A scan can establish only what the bound receiver profile and coverage artifact
support. Failure to observe Wi-Fi, BLE or any other feature cannot be generalized
to "the product emits no signal" without a revision-scoped evidentiary basis.

## Asset ontology

`vendor != product family != model/SKU != hardware revision != firmware era != emitter`

RF behavior never inherits across product families or revisions by vendor name.
A distributed ALPR installation may separate capture, recognition, compute,
gateway and backhaul across different physical components.

## Validation

Candidate discovery does not create a probability. The v0.1.1 validation gate
can advance a candidate only to `FIELD_TESTING`; the existing signature registry
remains authoritative for stricter `ACTIVE` promotion requirements.
