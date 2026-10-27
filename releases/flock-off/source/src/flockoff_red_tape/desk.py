# SPDX-License-Identifier: Apache-2.0
"""Desktop application operations, independent of the graphical interface."""
import copy
import hashlib
import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from .ledger import Ledger, private_write
from .model import Invalid, REVIEW_CHECKS, ready_errors, validate
from .render import packet, request_draft, timing, tracker


def now():
    return datetime.now(timezone.utc).isoformat()


def new_case(case_id, agency, meeting_date, agenda, decision, agenda_url,
             action, why, question, qualification):
    """Create an untimed, unreviewed case without fabricated supporting records."""
    return validate({
        'schema_version': '1.0', 'id': case_id, 'agency': agency,
        'meeting': {'date': meeting_date, 'agenda_item': agenda,
                    'decision': decision, 'url': agenda_url},
        'requested_action': action, 'why': {'text': why, 'claim_ids': []},
        'qualification': qualification, 'sources': [], 'claims': [],
        'questions': [{'id': 'Q01', 'subject': agenda, 'text': question,
                       'claim_ids': [], 'gap': question, 'follow_up': question,
                       'rank_reason': 'Initial question selected by the case author.', 'priority': 1}],
        'selected_questions': ['Q01'], 'answers': [], 'requests': [],
        'assessment': {f'T{i:02}': {'state': 'unanswered', 'evidence_ids': [],
                                  'explanation': 'Not yet assessed.'} for i in range(1, 13)},
    })


class Desk:
    def __init__(self, db, key, create=False):
        self.db, self.key = Path(db), Path(key)
        self.store = Ledger(self.db, self.key, create=create)

    def close(self):
        self.store.close()

    def cases(self):
        ids = self.store.db.execute('SELECT DISTINCT case_id FROM revisions ORDER BY case_id').fetchall()
        return [self.store.load(row[0]) for row in ids]

    def save(self, case, revision):
        updated = copy.deepcopy(case)
        updated.pop('review', None)
        return self.store.append(updated, revision)

    def attach(self, case_id, source_id, path, revision):
        case, receipt = self.store.load(case_id)
        if receipt['revision'] != revision:
            raise Invalid('stale revision: reload before attaching')
        source = next((s for s in case['sources'] if s['id'] == source_id), None)
        if source is None:
            raise Invalid('select an existing evidence source')
        with Path(path).open('rb') as stream:
            data = stream.read(20 * 1024 * 1024 + 1)
        if len(data) > 20 * 1024 * 1024:
            raise Invalid('document exceeds 20 MiB limit')
        sha = hashlib.sha256(data).hexdigest()
        if source.get('sha256') and source['sha256'] != sha:
            raise Invalid('different document: create a new source record')
        source['sha256'] = sha
        case.pop('review', None)
        return self.store.append(case, revision, {sha: data})

    def review(self, case_id, revision, reviewer, checks):
        if set(checks) != REVIEW_CHECKS:
            raise Invalid('all three review attestations are required')
        case, _ = self.store.load(case_id)
        case['review'] = {'reviewer': reviewer, 'at': now(), 'checks': sorted(checks)}
        return self.store.append(case, revision)

    def status(self, case, as_of=None):
        return {'errors': ready_errors(case), 'timing': timing(case),
                'tracker': tracker(case, as_of or date.today().isoformat())}

    def generate(self, case_id, revision, output, as_of, ready=False):
        # Render the exact revision visible to the operator, including its review.
        case, receipt = self.store.load(case_id, revision)
        files = packet(case, receipt, as_of, False, ready)
        output = Path(output)
        output.mkdir(parents=True, exist_ok=False, mode=0o700)
        for name, data in files.items():
            private_write(output / name, data)
        self.verify_packet(case_id, output)
        return output

    def verify_packet(self, case_id, directory):
        from .cli import strict_load
        directory = Path(directory)
        manifest = strict_load(directory / 'packet_receipt.json')
        case, receipt = self.store.load(case_id, manifest['revision_receipt']['revision'])
        if manifest['revision_receipt'] != receipt:
            raise Invalid('packet custody receipt mismatch')
        expected = packet(case, receipt, manifest['as_of'], manifest['humor'])
        if set(p.name for p in directory.iterdir()) != set(expected):
            raise Invalid('packet has missing or unexpected files')
        if any((directory / name).read_bytes() != data for name, data in expected.items()):
            raise Invalid('packet bytes differ from the recorded revision')
        return receipt

    def backup(self, directory):
        """Online SQLite snapshot, encrypted payloads, external key never copied."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=False, mode=0o700)
        snapshots = self.cases()  # Verify chains and attached bytes before backup.
        target = directory / 'accountability.sqlite'
        private_write(target, b'')
        destination = sqlite3.connect(target)
        try:
            self.store.db.backup(destination)
        finally:
            destination.close()
        with Ledger(target, self.key) as backup:
            for case, receipt in snapshots:
                if backup.load(case['id'])[1] != receipt:
                    raise Invalid('backup checkpoint mismatch; retry backup')
        private_write(directory / 'checkpoint.json', json.dumps({
            'created_at': now(), 'database_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'receipts': [receipt for _, receipt in snapshots],
            'key_included': False,
            'recovery': 'Open accountability.sqlite with the original external key. Keep that key backed up separately.'
        }, indent=2).encode())
        return directory
