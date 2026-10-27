# SPDX-License-Identifier: Apache-2.0
import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import Mock,patch
from flockoff_collaboration.cli import main
from flockoff_red_tape.ledger import windows_user_sid


class RelayCLITests(unittest.TestCase):
    def test_private_provision_schema_no_secret_output_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);database=root/'relay.db';output=root/'provision.json'
            stdout=io.StringIO();stderr=io.StringIO()
            with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
                self.assertEqual(main(['provision','--database',str(database),'--output',str(output)]),0)
                original=output.read_bytes()
                self.assertEqual(main(['provision','--database',str(database),'--output',str(output)]),1)
            value=json.loads(original);self.assertEqual(set(value),{'room','admin'})
            for secret in value.values():
                self.assertRegex(secret,'^[0-9a-f]{32}$')
                self.assertNotIn(secret,stdout.getvalue()+stderr.getvalue())
            self.assertEqual(output.read_bytes(),original)
            with contextlib.closing(sqlite3.connect(database)) as db:self.assertEqual(db.execute('select count(*) from spaces').fetchone()[0],1)
            if os.name=='nt':
                acl=subprocess.run(['icacls.exe',str(output)],capture_output=True,text=True,check=True).stdout
                self.assertNotIn('(I)',acl)
                # The current principal is explicitly granted; no inherited ACEs.
                sid=windows_user_sid()
                verify=subprocess.run(['icacls.exe',str(output),'/findsid','*'+sid],capture_output=True,text=True,check=True)
                self.assertIn(str(output),verify.stdout)
            else:self.assertEqual(stat.S_IMODE(output.stat().st_mode),0o600)
    def test_invalid_ports_fail_before_opening_database(self):
        with patch('flockoff_collaboration.cli.MailboxRelay') as relay,contextlib.redirect_stderr(io.StringIO()):
            for value in ['0','-1','65536','abc','1.5']:
                with self.assertRaises(SystemExit):main(['serve','--database','unused','--port',value])
            relay.assert_not_called()
    def test_mocked_serve_interrupt_closes_both_resources(self):
        relay=Mock();http=Mock();http.serve_forever.side_effect=KeyboardInterrupt
        with patch('flockoff_collaboration.cli.MailboxRelay',return_value=relay),patch('flockoff_collaboration.cli.server',return_value=http) as factory,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['serve','--database','synthetic.db','--port','8765']),0)
        factory.assert_called_once_with(relay,8765);http.server_close.assert_called_once();relay.close.assert_called_once()
    def test_server_bind_failure_redacts_exception_and_closes_database(self):
        relay=Mock();stderr=io.StringIO()
        with patch('flockoff_collaboration.cli.MailboxRelay',return_value=relay),patch('flockoff_collaboration.cli.server',side_effect=RuntimeError('SECRET_CAPABILITY')),contextlib.redirect_stderr(stderr):
            self.assertEqual(main(['serve','--database','synthetic.db','--port','8765']),1)
        self.assertNotIn('SECRET_CAPABILITY',stderr.getvalue());relay.close.assert_called_once()
    def test_no_public_bind_option(self):
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            main(['serve','--database','unused','--port','8765','--host','0.0.0.0'])
