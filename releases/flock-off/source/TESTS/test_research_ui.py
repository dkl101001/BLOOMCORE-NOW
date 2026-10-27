# SPDX-License-Identifier: Apache-2.0
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock
from flockoff_red_tape.research_ui import ResearchWorker,create_workspace,open_workspace

class ResearchUITests(unittest.TestCase):
    def test_worker_is_single_thread_rate_state_retained_no_initial_tick(self):
        store=Mock();store.memory.records.return_value=[];agent=Mock();threads=[]
        def factory(path,scope):threads.append(threading.get_ident());return store
        worker=ResearchWorker('synthetic','public scope',factory,lambda s:agent)
        try:
            self.assertTrue(worker.results.get(timeout=5)[0]);agent.tick.assert_not_called();agent.enable.assert_not_called()
            worker.submit('enable',urls=['https://example.org/public'],confirmed=True,public_scope='public scope',access_rules_reviewed=True)
            self.assertTrue(worker.results.get(timeout=5)[0])
            for _ in range(2):worker.submit('tick');self.assertTrue(worker.results.get(timeout=5)[0])
            self.assertEqual(agent.tick.call_count,2);self.assertNotEqual(threads[0],threading.get_ident())
            worker.submit('disable');self.assertTrue(worker.results.get(timeout=5)[0]);agent.disable.assert_called()
        finally:worker.close();worker.thread.join(5)
        self.assertFalse(worker.thread.is_alive());store.close.assert_called_once()
    def test_failure_redacts_source_errors_and_closes(self):
        store=Mock();store.memory.records.return_value=[];agent=Mock();agent.tick.side_effect=RuntimeError('PRIVATE_TOKEN')
        worker=ResearchWorker('synthetic','public',lambda *a:store,lambda s:agent)
        try:
            worker.results.get(timeout=5);worker.submit('tick');result=worker.results.get(timeout=5)
            self.assertFalse(result[0]);self.assertNotIn('PRIVATE_TOKEN',result[1])
        finally:worker.close();worker.thread.join(5)
    def test_dedicated_workspace_reopens_without_arbitrary_database_path(self):
        with tempfile.TemporaryDirectory() as d:
            path,scope=create_workspace(d,'public council documents')
            self.assertEqual(open_workspace(path.parent),(path,scope))
            with self.assertRaises((ValueError,FileNotFoundError)):open_workspace(d)
            import sqlite3
            connection=sqlite3.connect(path);connection.execute('CREATE TABLE private_records(secret TEXT)');connection.commit();connection.close()
            with self.assertRaises(ValueError):open_workspace(path.parent)
    def test_scope_required_before_workspace_creation(self):
        with tempfile.TemporaryDirectory() as d:
            for scope in ['', ' '*4, 'x'*129]:
                with self.assertRaises(ValueError):create_workspace(d,scope)
            self.assertEqual(list(Path(d).iterdir()),[])

    def test_actual_agent_retains_rate_limit_with_fixture_fetch(self):
        from flockoff_research.agent import ResearchAgent
        fetch=Mock();fetch.fetch.return_value='Synthetic council public record, status unconfirmed.'
        with tempfile.TemporaryDirectory() as d:
            path,scope=create_workspace(d,'public fixtures')
            worker=ResearchWorker(path,scope,agent_factory=lambda store:ResearchAgent(store,transport=fetch))
            try:
                self.assertTrue(worker.results.get(timeout=5)[0]);fetch.fetch.assert_not_called()
                worker.submit('enable',urls=['https://example.org/public'],confirmed=True,public_scope=scope,access_rules_reviewed=True)
                self.assertTrue(worker.results.get(timeout=5)[0])
                worker.submit('tick');result=worker.results.get(timeout=5)
                self.assertTrue(result[0]);self.assertEqual(len(result[2]),1)
                self.assertEqual(result[2][0]['claim_state'],'unknown')
                worker.submit('tick');self.assertTrue(worker.results.get(timeout=5)[0])
                fetch.fetch.assert_called_once_with('https://example.org/public')
            finally:worker.close();worker.thread.join(5)
            self.assertFalse(worker.thread.is_alive())
