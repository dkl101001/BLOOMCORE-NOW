# SPDX-License-Identifier: Apache-2.0
"""Encrypted append-only snapshots, optimistic concurrency, artifact-bound review."""

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import subprocess
import csv
import io
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from .model import Invalid, canonical, validate


@lru_cache(maxsize=1)
def windows_user_sid():
    result = subprocess.run(['whoami.exe', '/user', '/fo', 'csv', '/nh'],
                            capture_output=True, text=True, check=True,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    sid = next(csv.reader(io.StringIO(result.stdout.strip())))[1]
    if not sid.startswith('S-1-'):
        raise Invalid('could not determine Windows account SID')
    return sid


def private_write(path, data):
    """New artifacts never silently replace existing files."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        if os.name == 'nt':
            # Restrict the newly created empty file before writing sensitive bytes.
            subprocess.run(['icacls.exe', str(path), '/inheritance:r', '/grant:r',
                            '*' + windows_user_sid() + ':F'],
                           capture_output=True, check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


class Ledger:
    def __init__(self, path, key_path, create=False):
        path, key_path = Path(path), Path(key_path)
        if path.resolve() == key_path.resolve() or path.is_symlink() or key_path.is_symlink():
            raise Invalid('ledger and key must be distinct regular files')
        if create:
            if path.exists() or key_path.exists():
                raise Invalid('init refuses to replace an existing ledger or key')
            private_write(key_path, Fernet.generate_key())
            private_write(path, b'')
        if not path.is_file() or not key_path.is_file():
            raise Invalid('ledger and external key must already exist; use init')
        self.raw_key = key_path.read_bytes()
        self.fernet = Fernet(self.raw_key)
        self.mac_key = hmac.digest(base64.urlsafe_b64decode(self.raw_key), b'flockoff-red-tape:custody:v1', 'sha256')
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA secure_delete=ON')
        if create:
            self.db.execute('CREATE TABLE revisions (case_id TEXT, rev INTEGER, previous TEXT, mac TEXT, ciphertext BLOB, PRIMARY KEY(case_id,rev))')
            self.db.execute('CREATE TABLE approvals (digest TEXT PRIMARY KEY, ciphertext BLOB NOT NULL)')
            self.db.execute('CREATE TABLE documents (sha256 TEXT PRIMARY KEY, ciphertext BLOB NOT NULL)')
            self.db.execute("CREATE TRIGGER immutable_revision_update BEFORE UPDATE ON revisions BEGIN SELECT RAISE(ABORT,'immutable'); END")
            self.db.execute("CREATE TRIGGER immutable_revision_delete BEFORE DELETE ON revisions BEGIN SELECT RAISE(ABORT,'immutable'); END")
            self.db.execute("CREATE TRIGGER immutable_approval_update BEFORE UPDATE ON approvals BEGIN SELECT RAISE(ABORT,'immutable'); END")
            self.db.execute("CREATE TRIGGER immutable_approval_delete BEFORE DELETE ON approvals BEGIN SELECT RAISE(ABORT,'immutable'); END")
            self.db.execute("CREATE TRIGGER immutable_document_update BEFORE UPDATE ON documents BEGIN SELECT RAISE(ABORT,'immutable'); END")
            self.db.execute("CREATE TRIGGER immutable_document_delete BEFORE DELETE ON documents BEGIN SELECT RAISE(ABORT,'immutable'); END")

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _decrypt(self, value):
        try:
            return json.loads(self.fernet.decrypt(value))
        except (InvalidToken, ValueError) as exc:
            raise Invalid('custody authentication failed: wrong key or corrupted storage') from exc

    def _mac(self, case, rev, previous):
        body = {'case': case, 'revision': rev, 'previous': previous, 'algorithm': 'red-tape-snapshot-v1'}
        return hmac.digest(self.mac_key, canonical(body), 'sha256').hex()

    def verify(self, case_id):
        rows = self.db.execute('SELECT rev,previous,mac,ciphertext FROM revisions WHERE case_id=? ORDER BY rev', (case_id,)).fetchall()
        previous = ''
        for expected, (rev, prev, mac, ciphertext) in enumerate(rows, 1):
            case = validate(self._decrypt(ciphertext))
            if case['id'] != case_id or rev != expected or prev != previous or not hmac.compare_digest(mac, self._mac(case, rev, prev)):
                raise Invalid('revision chain does not verify')
            for source in case['sources']:
                sha = source.get('sha256')
                if sha and self.db.execute('SELECT 1 FROM documents WHERE sha256=?', (sha,)).fetchone():
                    self.read_document(sha)
            previous = mac
        return len(rows), previous

    def load(self, case_id, revision=None):
        self.verify(case_id)
        if revision is None:
            row = self.db.execute('SELECT rev,mac,ciphertext FROM revisions WHERE case_id=? ORDER BY rev DESC LIMIT 1', (case_id,)).fetchone()
        else:
            row = self.db.execute('SELECT rev,mac,ciphertext FROM revisions WHERE case_id=? AND rev=?', (case_id, revision)).fetchone()
        if row is None:
            raise Invalid('case/revision not found')
        return self._decrypt(row[2]), {'case_id': case_id, 'revision': row[0], 'custody_mac': row[1], 'algorithm': 'red-tape-snapshot-v1'}

    def append(self, case, expected_revision, documents=None):
        case = validate(case)
        documents = documents or {}
        for sha, data in documents.items():
            if not isinstance(data, bytes) or len(data) > 20 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != sha:
                raise Invalid('document must be bytes up to 20 MiB with matching SHA-256')
            if sha not in {s.get('sha256') for s in case['sources']}:
                raise Invalid('document is not referenced by this case revision')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            count, previous = self.verify(case['id'])
            if type(expected_revision) is not int or expected_revision != count:
                raise Invalid('stale revision: reload before editing')
            if count:
                old, _ = self.load(case['id'])
                # Preserve full answer history. Earlier request states remain in encrypted snapshots.
                if case['answers'][:len(old['answers'])] != old['answers']:
                    raise Invalid('answer history is append-only; append a correction instead')
                if old.get('review') == case.get('review') and old != case:
                    case.pop('review', None)
            mac = self._mac(case, count + 1, previous)
            for sha, data in documents.items():
                self.db.execute('INSERT OR IGNORE INTO documents VALUES(?,?)', (sha, self.fernet.encrypt(data)))
            self.db.execute('INSERT INTO revisions VALUES(?,?,?,?,?)', (case['id'], count + 1, previous, mac, self.fernet.encrypt(canonical(case))))
            self.db.execute('COMMIT')
        except Exception:
            self.db.execute('ROLLBACK')
            raise
        return {'case_id': case['id'], 'revision': count + 1, 'custody_mac': mac, 'algorithm': 'red-tape-snapshot-v1'}

    def read_document(self, sha):
        row = self.db.execute('SELECT ciphertext FROM documents WHERE sha256=?', (sha,)).fetchone()
        if row is None:
            raise Invalid('original document not held locally')
        try:
            data = self.fernet.decrypt(row[0])
        except InvalidToken as exc:
            raise Invalid('document custody authentication failed') from exc
        if hashlib.sha256(data).hexdigest() != sha:
            raise Invalid('document digest does not match ciphertext custody')
        return data

    def approve_artifact(self, data, reviewer, at, attested=False):
        from .model import instant, text
        text(reviewer, 'reviewer')
        instant(at, 'approval.at')
        if attested is not True:
            raise Invalid('explicit review of redactions and publication consent is required')
        sha = hashlib.sha256(data).hexdigest()
        record = {'sha256': sha, 'reviewer': reviewer, 'at': at, 'redactions_and_consent_reviewed': True}
        self.db.execute('INSERT INTO approvals VALUES(?,?)', (sha, self.fernet.encrypt(canonical(record))))
        return record

    def export_approved(self, data, output):
        sha = hashlib.sha256(data).hexdigest()
        row = self.db.execute('SELECT ciphertext FROM approvals WHERE digest=?', (sha,)).fetchone()
        if row is None or self._decrypt(row[0]).get('sha256') != sha:
            raise Invalid('these exact bytes have not been approved for public export')
        private_write(output, data)
        return {'sha256': sha, 'state': 'approved_local_export', 'published': False}
