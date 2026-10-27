# SPDX-License-Identifier: Apache-2.0
"""Defensive state invariants; synthetic local records, no external transport."""
import copy
import unittest
from unittest.mock import Mock
import test_owner_collaboration as fixtures
from flockoff_collaboration.protocol import uid,Rejected
from flockoff_collaboration.peer import Peer
from pathlib import Path

class QueueRecoveryTests(unittest.TestCase):
    setUp=fixtures.OwnerCollaborationTests.setUp
    tearDown=fixtures.OwnerCollaborationTests.tearDown
    pump=fixtures.OwnerCollaborationTests.pump
    card=fixtures.OwnerCollaborationTests.card
    sync=fixtures.OwnerCollaborationTests.sync
    def draft(self,peer,**changes):
        record={'schema_version':'draft/1','room_id':peer.state['invitation']['room'],'event_id':uid(),
            'author_room_key':peer.public_request()['sign_public'],'author_sequence':1,
            'previous_author_event':None,'parent_event_ids':[],'object_id':uid(),
            'operation':'revision','payload':self.card()}
        record.update(changes);return record
    def reopen(self,index):
        self.peers[index].close();root=Path(self.tmp.name)
        self.peers[index]=Peer(root/f'p{index}.sqlite',root/f'p{index}.key')
        return self.peers[index]
    def test_startup_sanitizes_invalid_local_pending_and_keeps_independent_records(self):
        for index,receiver in enumerate(self.peers):
            with self.subTest(receiver=index):
                bad=self.draft(receiver,author_sequence=2)
                good=self.draft(self.peers[(index+1)%3])
                receiver.state['pending']={bad['event_id']:bad,good['event_id']:good};receiver.save()
                receiver=self.reopen(index)
                self.assertNotIn(bad['event_id'],receiver.state['pending'])
                self.assertIn(good['event_id'],receiver.state['events'])
                self.assertEqual(receiver.state['quarantined'],1)
                receiver=self.reopen(index)
                self.assertEqual(receiver.state['quarantined'],1)
                self.assertFalse(receiver.state['pending'])
    def test_dependency_resolution_rejects_only_invalid_entry(self):
        a,b,c=self.peers;parent=self.draft(a)
        bad=self.draft(b,author_sequence=2,previous_author_event=parent['event_id'])
        good=self.draft(c)
        b.state['pending']={bad['event_id']:bad};b._drain_pending()
        self.assertIn(bad['event_id'],b.state['pending'])
        b.state['events'][parent['event_id']]=parent;b.state['pending'][good['event_id']]=good
        b._drain_pending()
        self.assertNotIn(bad['event_id'],b.state['pending']);self.assertIn(good['event_id'],b.state['events'])
        self.assertEqual(b.state['quarantined'],1)
    def test_known_invalid_dependency_is_rejected_while_other_parent_unknown(self):
        a,b,_=self.peers;parent=self.draft(a);b.state['events'][parent['event_id']]=parent
        invalid=self.draft(b,parent_event_ids=[parent['event_id'],uid()])
        b.state['pending'][invalid['event_id']]=invalid;b._drain_pending()
        self.assertFalse(b.state['pending']);self.assertEqual(b.state['quarantined'],1)
    def test_valid_out_of_order_chain_survives_restart_and_promotes(self):
        a,b,_=self.peers;first=self.draft(a)
        second=self.draft(a,author_sequence=2,previous_author_event=first['event_id'])
        b.state['pending'][second['event_id']]=second;b.save();b=self.reopen(1)
        self.assertIn(second['event_id'],b.state['pending']);self.assertEqual(b.state['quarantined'],0)
        b.state['events'][first['event_id']]=first;b._drain_pending()
        self.assertIn(second['event_id'],b.state['events']);self.assertFalse(b.state['pending'])
    def test_entire_outbox_preflight_has_zero_transport_calls(self):
        a=self.peers[0]
        for _ in range(10):a.queue(self.card())
        original=copy.deepcopy(a.state['queue'])
        for index in (0,1,9):
            for field in ('payload','parents','draft'):
                with self.subTest(index=index,field=field):
                    a.state['queue']=copy.deepcopy(original);item=a.state['queue'][index]
                    if field=='payload':item['payload']['private_path']='SYNTHETIC_PRIVATE'
                    elif field=='parents':item['parents']=['SYNTHETIC_PRIVATE']
                    else:item['draft']={'private_path':'SYNTHETIC_PRIVATE'}
                    transport=Mock()
                    with self.assertRaises(Rejected):a.sync(transport)
                    self.assertEqual(transport.mock_calls,[])
    def test_normal_multi_item_sync_keeps_dynamic_sequence(self):
        a,b,_=self.peers
        for index in range(3):a.queue(self.card(str(index)))
        self.sync(a);self.sync(b)
        self.assertEqual(a.state['sequence'],3);self.assertEqual(len(b.state['events']),3)
        self.assertFalse(a.state['queue'])
