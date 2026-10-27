PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ledger_events (
  event_kind TEXT NOT NULL,
  event_id TEXT NOT NULL,
  canonical_json TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  recorded_at_utc TEXT NOT NULL,
  PRIMARY KEY (event_kind, event_id),
  UNIQUE (content_hash)
);

CREATE TABLE IF NOT EXISTS node_revisions (
  node_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision >= 1),
  canonical_json TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  recorded_at_utc TEXT NOT NULL,
  PRIMARY KEY (node_id, revision),
  UNIQUE (content_hash)
);

CREATE TABLE IF NOT EXISTS source_edges (
  child_source_id TEXT NOT NULL,
  parent_source_id TEXT NOT NULL,
  relation TEXT NOT NULL CHECK (relation IN ('DERIVES_FROM', 'MIRRORS', 'CORROBORATES', 'CONTRADICTS')),
  PRIMARY KEY (child_source_id, parent_source_id, relation)
);

CREATE TABLE IF NOT EXISTS restricted_pose_ciphertexts (
  pose_id TEXT PRIMARY KEY,
  key_id TEXT NOT NULL,
  nonce BLOB NOT NULL,
  ciphertext BLOB NOT NULL,
  content_hash TEXT NOT NULL,
  recorded_at_utc TEXT NOT NULL,
  UNIQUE (content_hash)
);

CREATE TABLE IF NOT EXISTS schema_migrations (
  migration_id TEXT PRIMARY KEY,
  sql_sha256 TEXT NOT NULL,
  applied_at_utc TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS ledger_events_no_update
BEFORE UPDATE ON ledger_events BEGIN SELECT RAISE(ABORT, 'immutable ledger event'); END;
CREATE TRIGGER IF NOT EXISTS ledger_events_no_delete
BEFORE DELETE ON ledger_events BEGIN SELECT RAISE(ABORT, 'immutable ledger event'); END;
CREATE TRIGGER IF NOT EXISTS node_revisions_no_update
BEFORE UPDATE ON node_revisions BEGIN SELECT RAISE(ABORT, 'immutable node revision'); END;
CREATE TRIGGER IF NOT EXISTS node_revisions_no_delete
BEFORE DELETE ON node_revisions BEGIN SELECT RAISE(ABORT, 'immutable node revision'); END;
CREATE TRIGGER IF NOT EXISTS restricted_pose_no_update
BEFORE UPDATE ON restricted_pose_ciphertexts BEGIN SELECT RAISE(ABORT, 'immutable restricted pose'); END;
CREATE TRIGGER IF NOT EXISTS restricted_pose_no_delete
BEFORE DELETE ON restricted_pose_ciphertexts BEGIN SELECT RAISE(ABORT, 'immutable restricted pose'); END;
CREATE TRIGGER IF NOT EXISTS source_edges_no_update
BEFORE UPDATE ON source_edges BEGIN SELECT RAISE(ABORT, 'immutable source edge'); END;
CREATE TRIGGER IF NOT EXISTS source_edges_no_delete
BEFORE DELETE ON source_edges BEGIN SELECT RAISE(ABORT, 'immutable source edge'); END;
CREATE TRIGGER IF NOT EXISTS schema_migrations_no_update
BEFORE UPDATE ON schema_migrations BEGIN SELECT RAISE(ABORT, 'immutable migration custody'); END;
CREATE TRIGGER IF NOT EXISTS schema_migrations_no_delete
BEFORE DELETE ON schema_migrations BEGIN SELECT RAISE(ABORT, 'immutable migration custody'); END;
