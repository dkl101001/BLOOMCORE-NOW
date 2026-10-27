# SPDX-License-Identifier: Apache-2.0
"""Synthetic hostile cases; direct relay adapter performs no network I/O."""
import copy
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import test_owner_collaboration as fixtures
from flockoff_collaboration.peer import Peer
from flockoff_collaboration.owner import put, seal
from flockoff_collaboration.protocol import (
    Rejected, SigningKey, digest, parse, signed, uid, un64,
)


class CollaborationAdversarialTests(unittest.TestCase):
    setUp = fixtures.OwnerCollaborationTests.setUp
    tearDown = fixtures.OwnerCollaborationTests.tearDown
    pump = fixtures.OwnerCollaborationTests.pump
    sync = fixtures.OwnerCollaborationTests.sync
    card = fixtures.OwnerCollaborationTests.card

    def draft(self, peer, **changes):
        result = dict(schema_version='draft/1', room_id=peer.state['invitation']['room'],
                      event_id=uid(), author_room_key=peer.public_request()['sign_public'],
                      author_sequence=1, previous_author_event=None, parent_event_ids=[],
                      object_id=uid(), operation='revision', payload=self.card())
        result.update(changes)
        return result

    def grant(self, peer, draft):
        return peer.ask(self.t, 'grant', {'event_digest': digest(draft),
                        'expected_epoch': peer.state['epoch']}, owner_pump=self.pump, deadline=5)

    def delivery(self, peer, draft):
        response, _, _ = self.grant(peer, draft)
        grant = response['body']['result']
        return signed(dict(schema_version='delivery/1', draft=draft,
                           membership_epoch=grant['epoch'],
                           recipient_set_digest=digest(grant['roster']), grant=response),
                      SigningKey(un64(peer.state['identity']['sign_secret'])), 'delivery')

    def restart(self, index):
        self.peers[index].close()
        root = Path(self.tmp.name)
        self.peers[index] = Peer(root / f'p{index}.sqlite', root / f'p{index}.key')
        return self.peers[index]

    def test_consumed_grant_cannot_begin_second_batch(self):
        a = self.peers[0]; draft = self.draft(a)
        response, started, request = self.grant(a, draft)
        a.begin_batch(response, request, draft, started)
        with self.assertRaises(Rejected):
            a.begin_batch(response, request, draft, started)

    def test_restart_invalidates_unconsumed_and_consumed_grants(self):
        a = self.peers[0]; draft = self.draft(a)
        first = self.grant(a, draft); second = self.grant(a, draft)
        a.begin_batch(second[0], second[2], draft, second[1])
        a = self.restart(0)
        for response, started, request in (first, second):
            for in_batch in (False, True):
                with self.subTest(in_batch=in_batch), self.assertRaises(Rejected):
                    a.validate_grant(response, request, draft, started, in_batch=in_batch)

    def test_all_changed_request_bindings_and_wrong_owner_reject(self):
        a = self.peers[0]; draft = self.draft(a)
        response, started, request = self.grant(a, draft)
        variants = []
        for key, value in [('author', self.peers[1].public_request()['sign_public']),
                           ('room', uid()), ('nonce', uid())]:
            changed = copy.deepcopy(request); changed[key] = value; variants.append(changed)
        for key, value in [('expected_epoch', 999), ('event_digest', '0' * 64)]:
            changed = copy.deepcopy(request); changed['data'][key] = value; variants.append(changed)
        for changed in variants:
            with self.subTest(request=changed), self.assertRaises(Rejected):
                a.validate_grant(response, changed, draft, started)
        forged = signed(response['body'], SigningKey.generate(), 'owner-response')
        with self.assertRaises(Rejected): a.validate_grant(forged, request, draft, started)
        with self.assertRaises(Rejected): a.validate_grant(response, request, self.draft(a), started)

    def test_expiry_uses_monotonic_and_rollback_fails_closed(self):
        a = self.peers[0]; draft = self.draft(a)
        response, started, request = self.grant(a, draft)
        with patch('flockoff_collaboration.peer.time.monotonic', return_value=started + 31):
            with self.assertRaises(Rejected): a.begin_batch(response, request, draft, started)
        with patch('flockoff_collaboration.peer.time.time', return_value=a.state['last_clock'] - 100):
            with self.assertRaises(Rejected): a.begin_batch(response, request, draft, started)

    def test_response_after_request_deadline_is_not_live(self):
        a = self.peers[0]
        def late_pump():
            self.pump()
            time.sleep(.025)
        with self.assertRaises(ConnectionError):
            a.ask(self.t, 'grant', {'event_digest': digest(self.draft(a)),
                  'expected_epoch': a.state['epoch']}, owner_pump=late_pump, deadline=.01)
        self.assertFalse(a._grants); self.assertFalse(a._active)

    def test_removal_retains_inflight_window_but_new_grants_exclude_member(self):
        a, _, c = self.peers; draft = self.draft(a)
        old = self.delivery(a, draft)
        self.owner.remove(c.public_request()['sign_public'])
        # Historical exact batch remains readable: removal cannot retract it.
        c.receive(old)
        self.assertIn(draft['event_id'], c.state['events'])
        new = self.delivery(a, self.draft(a, author_sequence=2,
                           previous_author_event=draft['event_id']))
        with self.assertRaises(Rejected): c.receive(new)
        with self.assertRaises(ConnectionError):
            c.ask(self.t, 'grant', {'event_digest': digest(self.draft(c)),
                  'expected_epoch': c.state['epoch']}, owner_pump=self.pump, deadline=.03)

    def test_ack_loss_retries_same_packet_and_receiver_deduplicates(self):
        a, b, _ = self.peers; a.queue(self.card())
        owner_route = a.state['invitation']['owner_route']['route']
        attempts = []
        real_rpc = self.t.rpc
        def rpc(body):
            result = real_rpc(body)
            if body['action'] == 'put' and body['data']['route'] != owner_route:
                attempts.append(copy.deepcopy(body['data']))
                if len(attempts) == 1: raise ConnectionError('synthetic lost acknowledgement')
            return result
        # Owner uses original adapter so only sender deliveries lose acknowledgements.
        class Sender:
            pass
        sender = Sender(); sender.rpc = rpc
        a.sync(sender, owner_pump=self.pump, deadline=5)
        self.assertEqual(attempts[0], attempts[1])
        self.sync(b); self.assertEqual(len(b.state['events']), 1)
        b.state['cursor'] = 0; self.sync(b)
        self.assertEqual(len(b.state['events']), 1)

    def test_partial_send_restart_reprojects_after_removal(self):
        a, b, c = self.peers; a.queue(self.card())
        owner_route = a.state['invitation']['owner_route']['route']
        sent = []; real_rpc = self.t.rpc
        def rpc(body):
            if body['action'] == 'put' and body['data']['route'] != owner_route:
                sent.append(copy.deepcopy(body['data']))
                if len(sent) > 1: raise ConnectionError('synthetic interrupted batch')
            return real_rpc(body)
        class Sender:
            pass
        sender = Sender(); sender.rpc = rpc
        with self.assertRaises(ConnectionError): a.sync(sender, owner_pump=self.pump, deadline=5)
        old_packets = {d['packet'] for d in a.state['attempt']['deliveries']}
        removed_route = c.state['invitation']['mailbox']['route']
        self.owner.remove(c.public_request()['sign_public']); a = self.restart(0)
        resumed = []
        def capture(body):
            if body['action'] == 'put' and body['data']['route'] != owner_route:
                resumed.append(copy.deepcopy(body['data']))
            return real_rpc(body)
        sender.rpc = capture
        a.sync(sender, owner_pump=self.pump, deadline=5)
        self.assertTrue(resumed)
        self.assertNotIn(removed_route, [d['route'] for d in resumed])
        self.assertTrue(old_packets.isdisjoint({d['packet'] for d in resumed}))
        self.sync(b); self.assertEqual(len(b.state['events']), 1)
        self.assertFalse(a.state['queue'])

    def test_out_of_order_parent_buffers_then_resolves(self):
        a, b, _ = self.peers; first = self.draft(a)
        second = self.draft(a, object_id=first['object_id'], author_sequence=2,
                           previous_author_event=first['event_id'], parent_event_ids=[first['event_id']])
        one = self.delivery(a, first); two = self.delivery(a, second)
        b.receive(two); self.assertFalse(b.state['events'])
        self.assertIn(second['event_id'], b.state['pending'])
        b.receive(one); self.assertEqual(len(b.state['events']), 2)
        self.assertFalse(b.state['pending']); b.receive(two)
        self.assertEqual(len(b.state['events']), 2)

    def test_author_sequence_equivocation_rejected(self):
        a, b, _ = self.peers
        b.receive(self.delivery(a, self.draft(a)))
        with self.assertRaises(Rejected): b.receive(self.delivery(a, self.draft(a)))
        self.assertEqual(len(b.state['events']), 1)

    def test_missing_parent_buffer_is_bounded(self):
        a, b, _ = self.peers
        for sequence in range(2, 34):
            b.receive(self.delivery(a, self.draft(a, author_sequence=sequence, previous_author_event=uid())))
        self.assertEqual(len(b.state['pending']), 32)
        with self.assertRaises(Rejected):
            b.receive(self.delivery(a, self.draft(a, author_sequence=34, previous_author_event=uid())))
        self.assertEqual(len(b.state['pending']), 32)

    def test_private_fields_rejected_even_in_signed_remote_payload(self):
        a, b, _ = self.peers
        for key in ('private_path', 'database', 'sensor_session_id', 'reviewer_identity', 'original_file'):
            payload = dict(self.card(), **{key: 'SYNTHETIC_PRIVATE'})
            with self.subTest(key=key), self.assertRaises(Rejected):
                b.receive(self.delivery(a, self.draft(a, payload=payload)))
        self.assertFalse(b.state['events']); self.assertFalse(b.state['pending'])

    def test_crafted_outbox_private_fields_never_post(self):
        a = self.peers[0]; a.queue(self.card())
        a.state['queue'][0]['payload']['private_path'] = 'SYNTHETIC_PRIVATE'
        owner_route = a.state['invitation']['owner_route']['route']; posts = []
        real_rpc = self.t.rpc
        def capture(body):
            if body['action'] == 'put' and body['data']['route'] != owner_route: posts.append(body)
            return real_rpc(body)
        class Sender:
            pass
        sender = Sender(); sender.rpc = capture
        with self.assertRaises(Rejected): a.sync(sender, owner_pump=self.pump, deadline=5)
        self.assertEqual(len(posts), 0, 'private projection reached outbound recipient mailboxes')

    def test_deep_json_duplicate_keys_and_nonfinite_fail_closed(self):
        for raw in (b'[' * 12 + b'0' + b']' * 12,
                    b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(Rejected): parse(raw)

    def test_persisted_draft_private_extra_never_posts_after_restart(self):
        a = self.peers[0]; obj = a.queue(self.card())
        draft = self.draft(a, object_id=obj)
        draft['payload']['private_path'] = 'SYNTHETIC_PRIVATE'
        a.state['queue'][0]['draft'] = draft
        a.save(); a = self.restart(0)
        # No POST at all, including a grant request, is needed to reject this.
        with patch.object(self.t, 'rpc', wraps=self.t.rpc) as rpc:
            with self.assertRaises(Rejected): self.sync(a)
            self.assertFalse(any(call.args[0]['action'] == 'put' for call in rpc.call_args_list))

    def test_crafted_private_parent_never_posts(self):
        a = self.peers[0]; a.queue(self.card())
        a.state['queue'][0]['parents'] = ['C:/SYNTHETIC_PRIVATE/case.json']
        with patch.object(self.t, 'rpc', wraps=self.t.rpc) as rpc:
            with self.assertRaises(Rejected): self.sync(a)
            count = sum(call.args[0]['action'] == 'put' for call in rpc.call_args_list)
            self.assertEqual(count, 0, 'invalid private parent reached transport')

    def replay_owner_request(self, peer, request):
        inv = peer.state['invitation']
        document = signed(request, SigningKey(un64(peer.state['identity']['sign_secret'])), 'owner-request')
        put(self.t, inv['room'], inv['owner_route'], seal(inv['owner_encryption'], document))
        posts = []
        original = self.t.rpc
        def record(body):
            if body['action'] == 'put': posts.append(copy.deepcopy(body))
            return original(body)
        with patch.object(self.t, 'rpc', side_effect=record): self.pump()
        return posts

    def test_exact_owner_request_retry_reuses_identical_ciphertext_and_id(self):
        a = self.peers[0]; _, _, request = self.grant(a, self.draft(a))
        cached = copy.deepcopy(self.owner.state['responses'][request['nonce']])
        before = self.relay.db.execute('SELECT count(*) FROM packets').fetchone()[0]
        posts = self.replay_owner_request(a, request)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['data']['packet'], cached['packet'])
        self.assertEqual(posts[0]['data']['id'], cached['packet_id'])
        after = self.relay.db.execute('SELECT count(*) FROM packets').fetchone()[0]
        # Only the incoming retry is new; the response is relay-deduplicated.
        self.assertEqual(after, before + 1)

    def test_owner_request_nonce_with_changed_binding_is_quarantined(self):
        a = self.peers[0]; _, _, request = self.grant(a, self.draft(a))
        before = self.owner.state['quarantined']
        changed = copy.deepcopy(request); changed['data']['event_digest'] = 'f' * 64
        self.assertEqual(len(self.replay_owner_request(a, changed)), 0)
        self.assertEqual(self.owner.state['quarantined'], before + 1)


if __name__ == '__main__':
    unittest.main()
