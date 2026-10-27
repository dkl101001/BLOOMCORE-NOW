# Recovery, power-loss, and clock plan

Acknowledgment follows a committed `synchronous=FULL` SQLite transaction. The
field launcher must treat ENOSPC, I/O error, checksum failure and adapter loss as
visible state transitions, stop derivation when evidence may be incomplete, and
never manufacture coverage.

Required fault harness:

1. randomized kill before/after every transaction boundary for 1,000 runs;
2. compare acknowledged IDs with recovered immutable ledger IDs;
3. inject page/record corruption 100 times and require detection before
   inference;
4. fill disk and verify `DISK_FULL` plus explicit loss accounting;
5. unplug each sensor and verify coverage closure/health state;
6. jump wall clock backward/forward and reboot sensor; require new clock epoch,
   no cross-epoch TDoA and explicit timing contradiction;
7. restore read-only from last verified snapshot, preserving corrupt material for
   forensic receipt rather than silently repairing it.

SQLite integrity checks alone do not verify event content. Recovery must also
recompute canonical hashes and all referenced receipt inputs. A node whose
supporting evidence is unavailable becomes `EVIDENCE_UNAVAILABLE` or retracted;
it cannot remain publicly active.
