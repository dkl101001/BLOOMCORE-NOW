# SPDX-License-Identifier: AGPL-3.0-only
import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
import numpy as np
from flockoff_research.agent import ResearchStore, ResearchAgent
from flockoff_research.memory import cue, digest
from flockoff_research import _geometry

URL='https://council.example.org/minutes'

class PublicMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=Path(self.tmp.name)/'public.db'
        self.store=ResearchStore(self.path,scope='town-public')
    def tearDown(self):
        self.store.close(); self.tmp.cleanup()
    def add(self,text='Council purchased cameras.',**kwargs):
        return self.store.record(URL,text,category='council',claim_state='purchased',**kwargs)
    def test_pinned_core_and_typed_cue(self):
        self.assertEqual(hashlib.sha256(Path(_geometry.__file__).read_bytes()).hexdigest(),'c9b6e449002372d75f4dfdd50374c5c2018ca15a4df4633cbdd1a51aba146a6a')
        np.testing.assert_array_equal(cue('council','purchased'),cue('council','purchased'))
        self.assertFalse(np.array_equal(cue('council','planned'),cue('council','operating')))
        with self.assertRaises(ValueError):cue('secret-vault','planned')
    def test_actual_receiving_dedup_and_restart(self):
        class Fixture:
            def fetch(self,url):return 'Public minutes'
        agent=ResearchAgent(self.store,Fixture(),clock=lambda:100)
        agent.enable([URL],confirmed=True,public_scope='town-public',access_rules_reviewed=True)
        agent.tick()
        expected=_geometry.encounter(_geometry.initial(),cue('other','unknown'))
        self.assertEqual(self.store.memory.state(),(expected,1))
        original=self.store.history(URL)[0]
        self.assertEqual(self.store.record(URL,'Public minutes'),original)
        self.store.close(); self.store=ResearchStore(self.path,scope='town-public')
        self.assertEqual(self.store.memory.state(),(expected,1))
    def test_transaction_rollback_each_boundary(self):
        r=self.add(); before=self.store.memory.checkpoint()
        for boundary in ('evidence','encounter','checkpoint'):
            changed=dict(r,source_text='Changed public text',sha256=hashlib.sha256(b'Changed public text').hexdigest())
            def fault(stage):
                if stage==boundary:raise RuntimeError('synthetic interruption')
            with self.assertRaises(RuntimeError):self.store.memory.ingest(changed,fault)
            self.assertEqual(self.store.memory.checkpoint(),before)
    def test_query_nonmutation_and_receipt_independence(self):
        self.add(); before=self.store.memory.checkpoint()
        q=self.store.memory.query('council','purchased')
        self.assertGreater(q['response_delta'],0)
        self.assertIn('flat_distance',q['hits'][0])
        q['hits'][0]['record']['source_text']='Changed returned receipt'
        self.assertEqual(self.store.memory.checkpoint(),before)
    def test_material_revision_and_contradiction_eligible(self):
        self.add(); self.add('Installation cancelled.',contradictions=['Earlier purchase is not proof of operation.'])
        result=self.store.memory.query('map','operating')
        self.assertEqual(len(result['hits']),2)
        self.assertTrue(all(x['eligible'] for x in result['hits']))
        self.assertEqual(self.store.memory.state()[0]['tick'],2)
    def test_scope_and_mirror_isolation(self):
        self.add()
        self.store.record('https://archive.example.org/copy','Council purchased cameras.',category='council',claim_state='purchased')
        self.assertEqual(self.store.memory.state()[0]['tick'],1)
        other=ResearchStore(self.path,scope='different-public')
        try:
            self.assertEqual(other.memory.query('council','purchased')['hits'],[])
            self.assertEqual(other.memory.state()[0]['tick'],0)
        finally:other.close()
    def test_checkpoint_restore_and_corrupt_fail(self):
        self.add(); checkpoint=self.store.memory.checkpoint()
        target=ResearchStore(Path(self.tmp.name)/'restored.db',scope='town-public')
        try:
            corrupt=copy.deepcopy(checkpoint);corrupt['body']['state']['px'][0][0]=1.9
            corrupt['sha256']=digest(corrupt['body'])
            with self.assertRaises(ValueError):target.memory.restore(corrupt)
            self.assertEqual(target.memory.state()[1],0)
            target.memory.restore(checkpoint)
            self.assertEqual(target.memory.checkpoint(),checkpoint)
            with self.assertRaises(ValueError):target.memory.restore(checkpoint)
        finally:target.close()
    def test_local_corruption_never_resets(self):
        self.add()
        with self.store.db:self.store.db.execute("UPDATE public_geometry SET checksum='bad' WHERE scope='town-public'")
        with self.assertRaises(ValueError):self.store.memory.query('council','purchased')
        with self.assertRaises(ValueError):self.add('New text')
    def test_crafted_private_fields_rejected_without_mutation(self):
        r=self.add(); before=self.store.memory.checkpoint()
        with self.assertRaises(ValueError):self.store.memory.ingest(dict(r,private_vault_path='synthetic-private'))
        with self.assertRaises(ValueError):_geometry.encounter(_geometry.initial(),np.full((8,8),np.nan))
        self.assertEqual(self.store.memory.checkpoint(),before)

if __name__=='__main__':unittest.main()
