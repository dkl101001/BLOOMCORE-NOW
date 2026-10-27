# Migration policy

Migrations are append-only and content-hashed. The runtime executes the complete SQL
script and its checksum-custody row inside one explicit `BEGIN IMMEDIATE` /
`COMMIT` transaction. It splits statements with SQLite's parser and uses the
SQLite authorizer to deny transaction and savepoint opcodes regardless of line
layout, comments or aliases; any denied or failed statement rolls back the
transaction. They never rewrite or delete
historical event JSON. A migration receipt records the input schema and hash,
code and SQL digests, row counts, output hashes, quarantines, and the exact
reason for each demotion.

`0001_initial.sql` creates v1 storage. It is the only migration executed by the
working MVP.
