# SPDX-License-Identifier: Apache-2.0
import copy
import contextlib
import io
import hashlib
import json
import sqlite3
import os
import tempfile
import unittest
from pathlib import Path

from flockoff_red_tape.cli import main, strict_load
from flockoff_red_tape.ledger import Ledger
from flockoff_red_tape.model import Invalid, REVIEW_CHECKS, independence, ready_errors, validate
from flockoff_red_tape.render import packet, request_draft, timing, tracker

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples'
if not EXAMPLES.is_dir():
    EXAMPLES = ROOT / 'docs' / 'red_tape' / 'examples'


def case():
    return json.loads((EXAMPLES / 'case.json').read_text())


def reviewed(c):
    c['review'] = {'reviewer': 'Test reviewer', 'at': '2026-10-27T14:00:00Z', 'checks': sorted(REVIEW_CHECKS)}
    return c


class ModelTests(unittest.TestCase):
    def test_example_validates(self):
        validate(case())

    def test_unknown_fields_rejected(self):
        c = case(); c['observer_route'] = [[1, 2]]
        with self.assertRaises(Invalid): validate(c)

    def test_duplicate_ids_rejected(self):
        c = case(); c['sources'].append(copy.deepcopy(c['sources'][0]))
        with self.assertRaises(Invalid): validate(c)

    def test_dangling_evidence_rejected(self):
        c = case(); c['claims'][0]['evidence_ids'] = ['missing']
        with self.assertRaises(Invalid): validate(c)

    def test_five_mirrors_are_one_root(self):
        c = case()
        for i in range(5):
            s = copy.deepcopy(c['sources'][0]); s['id'] = f'M{i}'; s['parent_id'] = 'E01'; c['sources'].append(s)
        validate(c)
        self.assertEqual(independence(c, [s['id'] for s in c['sources']]), ['E01'])

    def test_lineage_cycles_rejected(self):
        c = case(); s = copy.deepcopy(c['sources'][0]); s['id'] = 'E02'; s['parent_id'] = 'E01'
        c['sources'][0]['parent_id'] = 'E02'; c['sources'].append(s)
        with self.assertRaises(Invalid): validate(c)

    def test_unverified_premise_stays_draft(self):
        c = reviewed(case()); c['claims'][0]['disposition'] = 'unverified'
        self.assertTrue(ready_errors(c))

    def test_open_question_is_not_claimed_fact(self):
        c = reviewed(case()); c['claims'][0].update(basis='open_question', evidence_ids=[], disposition='unverified', text='What is the notice window?')
        self.assertFalse(ready_errors(c))

    def test_review_required(self):
        self.assertTrue(ready_errors(case()))

    def test_superseded_document_blocks_ready(self):
        c = reviewed(case()); s = copy.deepcopy(c['sources'][0]); s['id'] = 'E02'
        c['sources'][0]['superseded_by'] = 'E02'; c['sources'].append(s)
        self.assertTrue(ready_errors(c))

    def test_documented_assessment_needs_evidence(self):
        c = case(); c['assessment']['T01']['state'] = 'documented'
        with self.assertRaises(Invalid): validate(c)

    def test_timed_brief_needs_rules(self):
        c = case(); c['meeting']['rules_verified'] = False
        with self.assertRaises(Invalid): validate(c)

    def test_unknown_allowance_is_untimed(self):
        c = case(); del c['meeting']['speaking_seconds']
        self.assertTrue(timing(validate(c))['untimed'])

    def test_more_than_three_questions_rejected(self):
        c = case()
        for i in range(2, 5):
            q = copy.deepcopy(c['questions'][0]); q['id'] = f'Q0{i}'; c['questions'].append(q); c['selected_questions'].append(q['id'])
        with self.assertRaises(Invalid): validate(c)

    def test_quote_requires_authentication(self):
        c = case(); a = json.loads((EXAMPLES / 'answer.json').read_text()); a['kind'] = 'quote'; c['answers'] = [a]
        with self.assertRaises(Invalid): validate(c)

    def test_partial_answer_preserves_gap(self):
        c = case(); c['answers'] = [json.loads((EXAMPLES / 'answer.json').read_text())]; validate(c)
        row = tracker(c, '2026-11-12')['questions'][0]
        self.assertEqual(row['status'], 'partial'); self.assertTrue(row['remaining_gap'])

    def test_no_invented_commitment(self):
        c = case(); a = json.loads((EXAMPLES / 'answer.json').read_text()); a['commitment']['agreed'] = False; c['answers'] = [a]
        with self.assertRaises(Invalid): validate(c)

    def test_legal_deadline_needs_verified_basis(self):
        c = case(); c['requests'][0]['legal_deadline'] = {'date': '2026-11-01'}
        with self.assertRaises(Invalid): validate(c)

    def test_reminder_is_not_legal_violation(self):
        r = tracker(case(), '2026-11-02')['requests'][0]
        self.assertTrue(r['review_due']); self.assertFalse(r['legal_violation_inferred'])

    def test_duplicate_request_guard(self):
        c = case(); r = copy.deepcopy(c['requests'][0]); r['id'] = 'R02'; r['fee_ceiling'] = '$20'; c['requests'].append(r)
        with self.assertRaises(Invalid): request_draft(c, 'R02')

    def test_no_follow_up_before_submission(self):
        with self.assertRaises(Invalid): request_draft(case(), 'R01', True)

    def test_request_is_local_draft(self):
        d = request_draft(case(), 'R01'); self.assertIn('not sent', d); self.assertNotIn('PRIVATE_CONTACT', d)

    def test_non_string_enums_rejected(self):
        c = case(); c['claims'][0]['basis'] = []
        with self.assertRaises(Invalid): validate(c)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.path = self.root / 'private.db'; self.key = self.root / 'private.key'
        self.store = Ledger(self.path, self.key, create=True)

    def tearDown(self):
        self.store.close(); self.tmp.cleanup()

    def test_payload_is_encrypted(self):
        self.store.append(case(), 0)
        raw = self.path.read_bytes()
        self.assertNotIn(b'PRIVATE_CONTACT', raw); self.assertNotIn(b'Example City', raw)
        if os.name != 'nt':
            self.assertEqual(self.key.stat().st_mode & 0o777, 0o600)

    def test_chain_and_reconstruction(self):
        self.store.append(case(), 0); self.store.append(reviewed(case()), 1)
        self.assertEqual(self.store.verify('demo-city-001')[0], 2)
        old, _ = self.store.load('demo-city-001', 1); self.assertNotIn('review', old)

    def test_stale_writer_refused(self):
        self.store.append(case(), 0)
        with self.assertRaises(Invalid): self.store.append(case(), 0)

    def test_sql_update_and_delete_refused(self):
        self.store.append(case(), 0)
        for sql in ('DELETE FROM revisions', "UPDATE revisions SET mac='bad'"):
            with self.assertRaises(sqlite3.IntegrityError): self.store.db.execute(sql)

    def test_answer_history_cannot_be_rewritten(self):
        c = case(); c['answers'].append(json.loads((EXAMPLES / 'answer.json').read_text())); self.store.append(c, 0)
        c['answers'][0]['text'] = 'A different answer'
        with self.assertRaises(Invalid): self.store.append(c, 1)

    def test_edit_invalidates_old_review(self):
        c = reviewed(case()); self.store.append(c, 0); c['requested_action'] = 'A revised action'; self.store.append(c, 1)
        self.assertNotIn('review', self.store.load(c['id'])[0])

    def test_wrong_key_cannot_read(self):
        from cryptography.fernet import Fernet
        self.store.append(case(), 0); other = self.root / 'wrong.key'; other.write_bytes(Fernet.generate_key())
        with Ledger(self.path, other) as wrong:
            with self.assertRaises(Invalid): wrong.load('demo-city-001')

    def test_export_requires_exact_reviewed_bytes(self):
        with self.assertRaises(Invalid): self.store.export_approved(b'candidate', self.root / 'out')
        self.store.approve_artifact(b'candidate', 'reviewer', '2026-10-27T14:00:00Z', True)
        with self.assertRaises(Invalid): self.store.export_approved(b'candidate changed', self.root / 'out')
        self.store.export_approved(b'candidate', self.root / 'out')
        self.assertEqual((self.root / 'out').read_bytes(), b'candidate')

    def test_explicit_consent_required(self):
        with self.assertRaises(Invalid): self.store.approve_artifact(b'test', 'r', '2026-10-27T14:00:00Z')

    def test_init_never_overwrites(self):
        with self.assertRaises(Invalid): Ledger(self.path, self.key, create=True)

    def test_document_original_retained_encrypted(self):
        c = case(); data = b'Original public contract bytes'; sha = hashlib.sha256(data).hexdigest()
        c['sources'][0]['sha256'] = sha
        self.store.append(c, 0, {sha: data})
        self.assertEqual(self.store.read_document(sha), data)
        self.assertNotIn(data, self.path.read_bytes())

    def test_document_failure_does_not_commit_revision(self):
        c = case()
        with self.assertRaises(Invalid): self.store.append(c, 0, {'a' * 64: b'wrong'})
        self.assertEqual(self.store.verify(c['id'])[0], 0)

    def test_case_verification_checks_attached_originals(self):
        c = case(); data = b'contract'; sha = hashlib.sha256(data).hexdigest()
        c['sources'][0]['sha256'] = sha; self.store.append(c, 0, {sha: data})
        self.store.db.execute('DROP TRIGGER immutable_document_update')
        self.store.db.execute('UPDATE documents SET ciphertext=?', (b'broken',))
        with self.assertRaises(Invalid): self.store.verify(c['id'])

    def test_ciphertext_tampering_detected(self):
        self.store.append(case(), 0)
        self.store.db.execute('DROP TRIGGER immutable_revision_update')
        self.store.db.execute("UPDATE revisions SET ciphertext=?", (b'corrupt',))
        with self.assertRaises(Invalid): self.store.verify('demo-city-001')

    def test_old_request_states_reconstruct(self):
        c = case(); self.store.append(c, 0)
        c['requests'][0].update(status='submitted', sent_at='2026-10-27', reference='actual-reference')
        self.store.append(c, 1)
        self.assertEqual(self.store.load(c['id'], 1)[0]['requests'][0]['status'], 'draft')
        self.assertEqual(self.store.load(c['id'])[0]['requests'][0]['status'], 'submitted')


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.c = reviewed(case()); self.receipt = {'case_id': self.c['id'], 'revision': 1, 'custody_mac': 'test-only'}

    def test_deterministic_packet(self):
        self.assertEqual(packet(self.c, self.receipt, '2026-10-27'), packet(self.c, self.receipt, '2026-10-27'))

    def test_manifest_binds_all_outputs(self):
        files = packet(self.c, self.receipt, '2026-10-27')
        for name, sha in json.loads(files['packet_receipt.json'])['files'].items():
            self.assertEqual(hashlib.sha256(files[name]).hexdigest(), sha)

    def test_private_fields_never_rendered(self):
        for output in packet(self.c, self.receipt, '2026-10-27').values():
            self.assertNotIn(b'PRIVATE_CONTACT', output); self.assertNotIn(b'PRIVATE_NOTES', output)

    def test_html_escapes_untrusted_documents(self):
        self.c['sources'][0]['content'] = '<script>alert(1)</script>'
        output = packet(self.c, self.receipt, '2026-10-27')['town_hall.html']
        self.assertNotIn(b'<script>alert', output); self.assertIn(b'&lt;script&gt;', output)
        self.assertIn(b"connect-src 'none'", output)

    def test_oversized_brief_cannot_be_ready(self):
        self.c['why']['text'] = 'evidence ' * 500
        with self.assertRaises(Invalid): packet(self.c, self.receipt, '2026-10-27', require_ready=True)

    def test_contrary_evidence_is_visible(self):
        self.c['claims'][0]['contrary_ids'] = ['E01']
        output = packet(self.c, self.receipt, '2026-10-27')['evidence_appendix.txt']
        self.assertIn(b'Contrary: E01', output)

    def test_cli_reconstructs_old_revision_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            root = Path(d); db, key, out = root / 'db', root / 'key', root / 'packet'
            args = ['--db', str(db), '--key', str(key)]
            self.assertEqual(main(args + ['init']), 0)
            self.assertEqual(main(args + ['import', str(EXAMPLES / 'case.json'), '--expected-revision', '0']), 0)
            self.assertEqual(main(args + ['review', self.c['id'], '--reviewer', 'Reviewer', '--attest-premises', '--attest-contrary-evidence', '--attest-meeting-rules']), 0)
            self.assertEqual(main(args + ['dispense', self.c['id'], '--output', str(out), '--as-of', '2026-10-27', '--ready']), 0)
            self.assertEqual(main(args + ['answer', self.c['id'], str(EXAMPLES / 'answer.json')]), 0)
            self.assertEqual(main(args + ['verify-packet', self.c['id'], '--directory', str(out)]), 0)
            (out / 'speaking_brief.txt').write_text('tampered')
            self.assertEqual(main(args + ['verify-packet', self.c['id'], '--directory', str(out)]), 2)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'a.json'; p.write_text('{"id":"a","id":"b"}')
            with self.assertRaises(Invalid): strict_load(p)

    def test_same_document_digest_deduplicates_without_parent(self):
        c = case(); c['sources'][0]['sha256'] = 'a' * 64
        s = copy.deepcopy(c['sources'][0]); s['id'] = 'E02'; s['url'] = 'https://mirror.example.org/copy'; c['sources'].append(s)
        self.assertEqual(independence(validate(c), ['E01', 'E02']), ['E01'])

    def test_flockoff_command_dispatch(self):
        from flockoff.cli import main as flockoff_main
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            args = ['red-tape', '--db', str(Path(d) / 'db'), '--key', str(Path(d) / 'key'), 'init']
            self.assertEqual(flockoff_main(args), 0)


if __name__ == '__main__':
    unittest.main()
