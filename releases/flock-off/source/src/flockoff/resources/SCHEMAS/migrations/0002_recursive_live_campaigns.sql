CREATE TABLE IF NOT EXISTS discovery_campaign_revisions (
  campaign_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision >= 1),
  canonical_json TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  recorded_at_utc TEXT NOT NULL,
  PRIMARY KEY (campaign_id, revision),
  UNIQUE (content_hash)
);

CREATE TRIGGER IF NOT EXISTS discovery_campaign_revisions_no_update
BEFORE UPDATE ON discovery_campaign_revisions BEGIN SELECT RAISE(ABORT, 'immutable discovery campaign revision'); END;
CREATE TRIGGER IF NOT EXISTS discovery_campaign_revisions_no_delete
BEFORE DELETE ON discovery_campaign_revisions BEGIN SELECT RAISE(ABORT, 'immutable discovery campaign revision'); END;
