# SPDX-License-Identifier: Apache-2.0
import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from flockoff_red_tape.desk import Desk, new_case
from flockoff_red_tape.ledger import windows_user_sid
from flockoff_red_tape.model import Invalid, REVIEW_CHECKS

ROOT = Path(__file__).resolve().parents[1]


class DeskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db, self.key = self.root / 'desk.sqlite', self.root / 'desk.key'
        self.desk = Desk(self.db, self.key, create=True)
        self.case = json.loads((ROOT / 'docs/red_tape/examples/case.json').read_text())

    def tearDown(self):
        self.desk.close()
        self.tmp.cleanup()

    def test_create_case_without_invented_evidence(self):
        case = new_case('test-1', 'Test body', '2026-10-27', 'Item 1', 'Review',
                        'https://example.org/agenda', 'Provide records.', 'Clarify scope.',
                        'What records exist?', 'No findings yet.')
        self.desk.save(case, 0)
        self.assertEqual(case['sources'], [])
        self.assertEqual(case['claims'], [])
        self.assertTrue(self.desk.status(case)['errors'])
        self.assertEqual(len(self.desk.cases()), 1)

    def test_full_persistence_packet_and_recovery(self):
        self.desk.save(self.case, 0)
        doc = self.root / 'record.txt'; doc.write_bytes(b'Test source document\n')
        self.desk.attach(self.case['id'], 'E01', doc, 1)
        self.desk.review(self.case['id'], 2, 'Test reviewer', REVIEW_CHECKS)
        packet = self.desk.generate(self.case['id'], 3, self.root / 'packet', '2026-10-27', True)
        self.desk.close()
        self.desk = Desk(self.db, self.key)
        self.assertEqual(self.desk.verify_packet(self.case['id'], packet)['revision'], 3)
        backup = self.desk.backup(self.root / 'backup')
        self.assertFalse(any(p.suffix == '.key' for p in backup.iterdir()))
        recovered = Desk(backup / 'accountability.sqlite', self.key)
        try:
            case, receipt = recovered.cases()[0]
            self.assertEqual(receipt['revision'], 3)
            self.assertEqual(recovered.store.read_document(case['sources'][0]['sha256']), doc.read_bytes())
            recovered.verify_packet(case['id'], packet)
        finally:
            recovered.close()
        edited, _ = self.desk.store.load(self.case['id'])
        edited['requested_action'] = 'Another action.'
        self.desk.save(edited, 3)
        self.assertNotIn('review', self.desk.store.load(self.case['id'])[0])
        self.desk.verify_packet(self.case['id'], packet)

    def test_stale_attachment_does_not_mutate_store(self):
        self.desk.save(self.case, 0)
        doc = self.root / 'record'; doc.write_bytes(b'public test')
        with self.assertRaisesRegex(Invalid, 'stale'):
            self.desk.attach(self.case['id'], 'E01', doc, 0)
        self.assertEqual(self.desk.store.verify(self.case['id'])[0], 1)
        self.assertEqual(self.desk.store.db.execute('SELECT count(*) FROM documents').fetchone()[0], 0)

    def test_tampering_and_overwrite_refused(self):
        self.desk.save(self.case, 0)
        output = self.desk.generate(self.case['id'], 1, self.root / 'packet', '2026-10-27')
        with self.assertRaises(FileExistsError):
            self.desk.generate(self.case['id'], 1, output, '2026-10-27')
        (output / 'speaking_brief.txt').write_text('tampered')
        with self.assertRaisesRegex(Invalid, 'bytes differ'):
            self.desk.verify_packet(self.case['id'], output)

    def test_reviews_require_all_checks_and_current_revision(self):
        self.desk.save(self.case, 0)
        with self.assertRaises(Invalid): self.desk.review(self.case['id'], 1, 'Reviewer', [])
        with self.assertRaises(Invalid): self.desk.review(self.case['id'], 0, 'Reviewer', REVIEW_CHECKS)
        with self.assertRaises(Invalid): self.desk.generate(self.case['id'], 1, self.root / 'no-packet', '2026-10-27', True)
        self.assertFalse((self.root / 'no-packet').exists())

    def test_import_cannot_carry_review_into_desk(self):
        self.case['review'] = {'reviewer': 'Old reviewer', 'at': '2026-10-27T00:00:00Z', 'checks': sorted(REVIEW_CHECKS)}
        self.desk.save(self.case, 0)
        self.assertNotIn('review', self.desk.store.load(self.case['id'])[0])

    @unittest.skipUnless(os.name == 'nt', 'Windows DACL validation')
    def test_windows_private_files_have_only_current_user_access(self):
        # Inspect the actual ACL rather than treating POSIX mode bits as Windows permissions.
        script = "$ErrorActionPreference='Stop'; $a=[System.IO.File]::GetAccessControl($args[0]); [pscustomobject]@{Protected=$a.AreAccessRulesProtected; Rules=@($a.Access | ForEach-Object { [pscustomobject]@{SID=$_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value; Inherited=$_.IsInherited; Type=$_.AccessControlType.ToString(); Rights=$_.FileSystemRights.ToString()} })} | ConvertTo-Json -Depth 4"
        for path in (self.key, self.db):
            result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', '& { ' + script + ' }', str(path)], capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            acl = json.loads(result.stdout)
            self.assertTrue(acl['Protected'])
            self.assertEqual(len(acl['Rules']), 1)
            rule = acl['Rules'][0]
            self.assertEqual(rule['SID'], windows_user_sid())
            self.assertFalse(rule['Inherited'])
            self.assertEqual(rule['Type'], 'Allow')
            self.assertEqual(rule['Rights'], 'FullControl')


if __name__ == '__main__': unittest.main()
