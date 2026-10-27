# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
import time
from pathlib import Path
from unittest.mock import patch,Mock
from nacl.signing import SigningKey
from flockoff_collaboration.protocol import *
from flockoff_collaboration.mailbox import MailboxRelay
from flockoff_collaboration.owner import RoomOwner,get,decrypt
from flockoff_collaboration.peer import Peer
from flockoff_collaboration.transport import Transport

class Direct:
    def __init__(self,relay):self.relay=relay
    def rpc(self,body):return self.relay.rpc(body)

class OwnerCollaborationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();p=Path(self.tmp.name)
        self.relay=MailboxRelay(p/'relay.sqlite');self.t=Direct(self.relay)
        self.owner=RoomOwner(p/'owner.sqlite',p/'owner.key',True)
        self.owner.initialize(self.relay.create_space(),self.t,'http://127.0.0.1:9999')
        self.peers=[Peer(p/f'p{i}.sqlite',p/f'p{i}.key',True) for i in range(3)]
        for peer in self.peers:
            invitation=self.owner.make_invite(peer.public_request(),self.t)
            peer.accept_invite(invitation,fingerprint_confirmed=True)
            peer.join(self.t,owner_pump=self.pump,deadline=5)
            peer.consent(['question','comment'],confirmed=True)
    def pump(self):self.owner.pump(self.t)
    def sync(self,peer):peer.sync(self.t,owner_pump=self.pump,deadline=5)
    def tearDown(self):
        for peer in self.peers:peer.close()
        self.owner.close();self.relay.close();self.tmp.cleanup()
    def card(self,text='Synthetic'):return {'category':'question','title':'Synthetic card','text':text}
    def test_three_clients_conflicts_merge(self):
        a,b,c=self.peers;obj=a.queue(self.card());self.sync(a);self.sync(b);self.sync(c)
        parent=b.heads(obj)[0]['event_id'];b.queue(self.card('B'),obj,[parent]);c.queue(self.card('C'),obj,[parent])
        self.sync(b);self.sync(c);self.sync(a);self.assertEqual(len(a.heads(obj)),2)
        a.queue(self.card('merged'),obj,[e['event_id'] for e in a.heads(obj)]);self.sync(a);self.sync(b)
        self.assertEqual(len(b.heads(obj)),1)
    def test_offline_owner_queues_and_reconnect(self):
        a=self.peers[0];a.queue(self.card())
        with self.assertRaises(ConnectionError):a.sync(self.t,deadline=.05)
        self.assertEqual(a.status,'Room owner offline: saved locally, sync queued')
        self.assertEqual(len(a.state['queue']),1)
        self.sync(a);self.assertFalse(a.state['queue'])
    def test_remove_blocks_new_grants_and_invites(self):
        a,b,c=self.peers;c.queue(self.card());self.owner.remove(c.public_request()['sign_public'])
        with self.assertRaises(ConnectionError):c.sync(self.t,owner_pump=self.pump,deadline=.05)
        self.assertEqual(len(c.state['queue']),1)
        a.queue(self.card());self.sync(a);self.sync(b)
        self.assertEqual(len(b.state['events']),1);self.assertFalse(c.state['events'])
    def test_leave_pauses(self):
        c=self.peers[2];c.leave(self.t,owner_pump=self.pump,deadline=5)
        self.assertFalse(c.state['consent'])
        self.assertNotIn(c.public_request()['sign_public'],self.owner.state['members'])
    def test_consent_and_projection_closed(self):
        a=self.peers[0];a.pause()
        with self.assertRaises(Rejected):a.queue(self.card())
        with self.assertRaises(Rejected):a.consent(['question'])
        a.consent(['question'],confirmed=True)
        for key in ('reviewer','route','private_path','session_id','database'):
            with self.assertRaises(Rejected):a.queue({**self.card(),key:'private'})
    def test_relay_cannot_read_author_or_content_or_sign_grants(self):
        a=self.peers[0];text='SYNTHETIC_SECRET_9284';a.queue(self.card(text));self.sync(a)
        raw=self.relay.path.read_bytes()
        self.assertNotIn(text.encode(),raw);self.assertNotIn(a.public_request()['sign_public'].encode(),raw)
        self.assertNotIn(self.owner.state['identity']['sign_secret'].encode(),raw)
    def test_replay_delivery_dedup(self):
        a,b,_=self.peers;obj=a.queue(self.card());self.sync(a);self.sync(b)
        count=len(b.state['events']);b.state['cursor']=0;self.sync(b)
        self.assertEqual(len(b.state['events']),count)
    def test_grant_nonce_digest_sender_room_epoch_and_signer_bindings(self):
        a=self.peers[0];a.queue(self.card());item=a.state['queue'][0]
        draft={'arbitrary':'synthetic digest only'}
        response,started,request=a.ask(self.t,'grant',{'event_digest':digest(draft),'expected_epoch':a.state['epoch']},owner_pump=self.pump,deadline=5)
        a.validate_grant(response,request,draft,started)
        for field,value in [('nonce',uid()),('author','wrong'),('room',uid())]:
            changed=dict(request);changed[field]=value
            if field=='nonce':
                with self.assertRaises(Rejected):a.validate_grant(response,changed,draft,started)
        with self.assertRaises(Rejected):a.validate_grant(response,request,{'changed':True},started)
        forged=signed(response['body'],SigningKey.generate(),'owner-response')
        with self.assertRaises(Rejected):a.validate_grant(forged,request,draft,started)
        with self.assertRaises(Rejected):a.validate_grant(response,request,draft,time.monotonic()-31)
    def test_restart_has_no_live_grant_and_clock_rollback(self):
        a=self.peers[0];a.state['last_clock']=int(time.time())+100;a.queue(self.card())
        with self.assertRaises(Rejected):self.sync(a)
        self.assertFalse(a._active)
    def test_payload_limits_and_json_rejections(self):
        with self.assertRaises(Rejected):projection(self.card('x'*3001))
        with self.assertRaises(Rejected):parse(b'{"a":1,"a":2}')
        with self.assertRaises(Rejected):parse(b'{"x":NaN}')
        with self.assertRaises(Rejected):parse(b' '*65537)
    def test_no_direct_fallback(self):
        with self.assertRaises(Rejected):Transport('https://example.com')
        with self.assertRaises(Rejected):Transport('http://127.0.0.1:1234')
        key=b'x'*32;host=base64.b32encode(key+hashlib.sha3_256(b'.onion checksum'+key+b'\x03').digest()[:2]+b'\x03').decode().lower()+'.onion'
        t=Transport('http://'+host)
        with patch('flockoff_collaboration.transport.requests.Session') as factory:
            import requests
            session=factory.return_value.__enter__.return_value;session.post.side_effect=requests.ConnectionError('offline')
            with self.assertRaises(ConnectionError):t.rpc({'test':True})
            self.assertFalse(session.trust_env);self.assertFalse(session.post.call_args.kwargs['allow_redirects'])
            self.assertTrue(session.post.call_args.kwargs['proxies']['http'].startswith('socks5h://'))
            self.assertEqual(session.post.call_count,1)
