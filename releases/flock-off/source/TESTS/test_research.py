# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
import requests
from flockoff_research.agent import *

class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=ResearchStore(Path(self.tmp.name)/'public.sqlite')
        self.transport=Mock();self.transport.fetch.return_value='A contract proposes cameras.'
        self.clock=Mock(return_value=1000);self.agent=ResearchAgent(self.store,self.transport,self.clock)
        self.url='https://records.example.org/council.txt'
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def enable(self):self.agent.enable([self.url],confirmed=True,public_scope='Public council contracts',access_rules_reviewed=True)
    def test_disabled_startup_and_app_active_only(self):
        self.assertIsNone(self.agent.tick());self.transport.fetch.assert_not_called()
        self.enable();self.assertIsNone(self.agent.tick(app_active=False));self.transport.fetch.assert_not_called()
    def test_explicit_scope_required(self):
        with self.assertRaises(ResearchError):self.agent.enable([self.url])
    def test_watchlist_rate_and_failure_backoff(self):
        self.enable();self.agent.tick();self.agent.tick();self.assertEqual(self.transport.fetch.call_count,1)
        self.clock.return_value=4600;self.transport.fetch.side_effect=ResearchError('offline')
        with self.assertRaises(ResearchError):self.agent.tick()
        self.agent.tick();self.assertEqual(self.transport.fetch.call_count,2)
    def test_history_and_exact_excerpts_no_confidence(self):
        self.store.record(self.url,'Planned cameras',claim_state='planned',excerpt='Planned',questions=['Installed?'])
        self.store.record(self.url,'Purchased cameras',claim_state='purchased',contradictions=['Earlier record only planned'])
        history=self.store.history(self.url);self.assertEqual(len(history),2)
        self.assertEqual(history[0]['claim_state'],'planned');self.assertNotIn('confidence',history[0])
        with self.assertRaises(ResearchError):self.store.record(self.url,'A',excerpt='B')
    def test_public_prior_not_measurement(self):
        self.enable();result=self.agent.tick()
        self.assertEqual(result['claim_state'],'unknown')
        self.assertEqual(result['evidence_basis'],'PUBLIC_RECORD_PRIOR_NOT_LOCAL_MEASUREMENT')
        self.assertEqual('PUBLIC_SOURCE_BOUND_CONDUCTANCE_MEMORY_V1',self.agent.memory_status)
    def test_bad_urls(self):
        for url in ['http://example.org/a','https://127.0.0.1/a','https://[::1]/a','https://169.254.169.254/a','https://10.0.0.1/a','https://localhost/a','https://x.local/a','https://user:pass@example.org/a','https://example.org/a?private=query']:
            with self.subTest(url=url),self.assertRaises(ResearchError):public_url(url)
    def test_tor_no_fallback_no_environment(self):
        with patch('flockoff_research.agent.requests.Session') as factory:
            session=factory.return_value.__enter__.return_value;session.get.side_effect=requests.ConnectionError('unavailable')
            with self.assertRaises(ResearchError):PublicTransport().fetch(self.url)
            self.assertFalse(session.trust_env);self.assertEqual(session.get.call_count,1)
            args=session.get.call_args.kwargs;self.assertFalse(args['allow_redirects']);self.assertTrue(args['proxies']['https'].startswith('socks5h://'))
    def test_redirect_rejected(self):
        with patch('flockoff_research.agent.requests.Session') as factory:
            response=factory.return_value.__enter__.return_value.get.return_value.__enter__.return_value;response.status_code=302
            with self.assertRaises(ResearchError):PublicTransport().fetch(self.url)
            response.iter_content.assert_not_called()
