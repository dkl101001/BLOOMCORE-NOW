# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from cryptography.fernet import Fernet
from flockoff_red_tape.document_variants import VariantStore, DISCLOSURE
from flockoff_red_tape.model import Invalid

class DocumentVariantTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.key=Fernet.generate_key();self.store=VariantStore(self.root/'private',self.key)
    def tearDown(self):self.tmp.cleanup()
    def create(self,**kw):return self.store.create('meeting','Synthetic source claim remains unchanged.','private-case-123',**kw)
    def test_titles_and_references_vary_without_source_mutation(self):
        with patch('flockoff_red_tape.document_variants.secrets.choice',side_effect=['Meeting Preparation Brief','Meeting Discussion Brief']):
            a=self.create();b=self.create()
        self.assertNotEqual(a.reference,b.reference);self.assertNotEqual(a.title,b.title)
        for p in (a,b):self.assertIn(b'Synthetic source claim remains unchanged.',p.data)
    def test_private_mapping_survives_reopen_and_is_not_exported(self):
        p=self.create();reopen=VariantStore(self.root/'private',self.key)
        self.assertEqual(reopen.recover_source(p.reference),'private-case-123')
        self.assertNotIn(b'private-case-123',p.data)
        self.assertNotIn(b'private-case-123',(self.root/'private'/ (p.reference+'.variant')).read_bytes())
    def test_each_variant_requires_preview_and_separate_approval(self):
        a=self.create();b=self.create();self.store.approve(a.reference,a.sha256,reviewer='Synthetic reviewer',consent=True)
        with self.assertRaises(Invalid):self.store.export(b.reference,b.sha256,self.root/'b.txt')
        with self.assertRaises(Invalid):self.store.export(a.reference,b.sha256,self.root/'wrong.txt')
        with self.assertRaises(Invalid):self.store.approve(b.reference,a.sha256,reviewer='Reviewer',consent=True)
    def test_reprint_preserves_exact_approved_bytes(self):
        a=self.create();self.store.approve(a.reference,a.sha256,reviewer='Reviewer',consent=True)
        for name in ['one.txt','two.txt']:self.store.export(a.reference,a.sha256,self.root/name)
        self.assertEqual((self.root/'one.txt').read_bytes(),(self.root/'two.txt').read_bytes())
        self.assertEqual(self.store.preview(a.reference),a)
    def test_unbranded_retains_disclosures(self):
        a=self.create(unbranded=True)
        self.assertNotIn(b'FLOCK OFF',a.data);self.assertIn(DISCLOSURE.encode(),a.data)
    def test_presenter_is_separate_and_explicit(self):
        with self.assertRaises(Invalid):self.create(presenter='Synthetic Presenter')
        p=self.create(presenter='Synthetic Presenter',disclose_presenter=True)
        self.assertIn(b'Presenter: Synthetic Presenter',p.data)
        self.assertNotIn(b'collaborator',p.data)
    def test_collision_is_retried_and_existing_variant_preserved(self):
        a=self.create()
        with patch('flockoff_red_tape.document_variants.secrets.token_hex',side_effect=[a.reference,'a'*32]):b=self.create()
        self.assertEqual(b.reference,'a'*32);self.assertEqual(self.store.preview(a.reference),a)
