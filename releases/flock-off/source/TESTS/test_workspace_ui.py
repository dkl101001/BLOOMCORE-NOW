# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path
from flockoff_red_tape.workspace_ui import PrivateNotebook

class PrivateNotebookTests(unittest.TestCase):
    def test_neutral_note_persists_encrypted_with_revisions(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);store=PrivateNotebook(root/'notes',root/'key',True)
            store.save('Personal note','SYNTHETIC_PRIVATE_NOTE');store.save('Follow-up','Synthetic revision')
            reopened=PrivateNotebook(root/'notes',root/'key')
            self.assertEqual(reopened.read()['revision'],2)
            self.assertEqual(reopened.read()['text'],'Synthetic revision')
            self.assertNotIn(b'SYNTHETIC_PRIVATE_NOTE',(root/'notes/revision-00000001.enc').read_bytes())
            self.assertEqual(len(reopened.revisions()),2)
    def test_key_must_be_external_and_creation_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(ValueError):PrivateNotebook(root/'notes',root/'notes/key',True)
            PrivateNotebook(root/'notes',root/'key',True)
            with self.assertRaises(ValueError):PrivateNotebook(root/'notes',root/'key',True)


class BranchTests(unittest.TestCase):
    def test_selection_retains_exact_parents_and_rejects_cross_object(self):
        from flockoff_red_tape.workspace_ui import select_branches
        events=[{'event_id':'a','object_id':'one'},{'event_id':'b','object_id':'one'},{'event_id':'c','object_id':'two'}]
        self.assertEqual([e['event_id'] for e in select_branches(events,['a','b'],True)],['a','b'])
        self.assertEqual(select_branches(events,['a'])[0]['event_id'],'a')
        for selection,merge in [(['a'],True),(['a','c'],True),(['missing'],False),(['a','b'],False)]:
            with self.assertRaises(ValueError):select_branches(events,selection,merge)


class WorkerTests(unittest.TestCase):
    def test_owner_worker_serializes_and_hides_failure_details(self):
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        import queue,threading
        from flockoff_red_tape.workspace_ui import OwnerConsole
        ui=SimpleNamespace(busy=False,paths=('synthetic.db','synthetic.key'),controls=[Mock()],endpoint=Mock(),results=queue.Queue())
        owner=Mock();owner.state={'endpoint':'synthetic','identity':{'sign_public':'public'}}
        owner.roster.return_value=[]
        owner.pump.side_effect=ValueError('SECRET_DO_NOT_DISPLAY')
        threads=[]
        def construct(*args,**kwargs):threads.append(threading.get_ident());return owner
        with patch('flockoff_collaboration.owner.RoomOwner',side_effect=construct) as factory,patch('flockoff_collaboration.transport.Transport'):
            OwnerConsole.run(ui,'pump')
            result=ui.results.get(timeout=5)
            OwnerConsole.run(ui,'pump') # busy until UI consumes result; cannot open a second connection
            self.assertEqual(factory.call_count,1)
        self.assertFalse(result[0]);self.assertNotIn('SECRET',result[2]);self.assertNotEqual(threads[0],threading.get_ident())
        owner.close.assert_called_once()
    def test_revision_queue_preserves_selected_parents(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from flockoff_red_tape.workspace_ui import WorkspacePaths
        peer=Mock()
        ui=SimpleNamespace(category=Mock(),card_title=Mock(),card=Mock(),edit_object='object',edit_parents=['a','b'],status=Mock(),with_peer=lambda fn:fn(peer))
        ui.category.get.return_value='question';ui.card_title.get.return_value='Synthetic';ui.card.get.return_value='Merged text'
        WorkspacePaths.queue_card(ui)
        peer.queue.assert_called_once_with({'category':'question','title':'Synthetic','text':'Merged text'},object_id='object',parents=['a','b'])
        self.assertIsNone(ui.edit_parents)

    def test_owner_real_encrypted_vault_invite_and_remove_with_mock_transport(self):
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        import queue,json
        from flockoff_red_tape.workspace_ui import OwnerConsole
        from flockoff_collaboration.owner import RoomOwner
        from flockoff_collaboration.protocol import new_identity,public_identity,uid
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);ui=SimpleNamespace(busy=False,paths=(str(base/'owner.db'),str(base/'key')),controls=[],endpoint=Mock(),results=queue.Queue())
            def run(action,**kwargs):
                ui.busy=False;OwnerConsole.run(ui,action,**kwargs)
                result=ui.results.get(timeout=5)
                self.assertTrue(result[0],result[2]);return result
            with patch('flockoff_collaboration.transport.Transport') as transport:
                transport.return_value.rpc.return_value={'route':uid(),'read':uid(),'write':uid()}
                run('open',create=True)
                run('initialize',provision={'room':uid(),'admin':uid()},url='synthetic fixture transport')
                member=public_identity(new_identity())
                run('invite',public=member,target=str(base/'invitation.json'))
                self.assertIsInstance(json.loads((base/'invitation.json').read_text()),str)
                owner=RoomOwner(*ui.paths)
                invite=next(iter(owner.state['invites'].values()))
                owner.state['members'][member['sign_public']]=invite;owner.save();owner.close()
                self.assertEqual(len(run('list')[1]),1)
                self.assertEqual(run('remove',member=member['sign_public'])[1],[])
                owner=RoomOwner(*ui.paths)
                self.assertEqual(owner.state['epoch'],2);self.assertEqual(owner.state['invites'],{});owner.close()
            self.assertNotIn(member['sign_public'].encode(),(base/'owner.db').read_bytes())
