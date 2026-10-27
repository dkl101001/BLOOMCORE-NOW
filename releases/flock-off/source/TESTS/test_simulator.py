# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import unittest
import tempfile
from flockoff_red_tape.simulator import SimulatorState, REJECTION, STAGES
from flockoff_red_tape.cli import strict_load
from flockoff_red_tape.model import validate


class SimulatorTests(unittest.TestCase):
    def test_seeded_process_is_repeatable_and_varies(self):
        self.assertEqual(SimulatorState(seed=42).stages, SimulatorState(seed=42).stages)
        self.assertGreater(len({SimulatorState(seed=i).stages for i in range(10)}), 1)

    def test_all_seeded_processes_end_with_rejection_only_after_last_stage(self):
        for seed in range(20):
            state = SimulatorState(seed=seed)
            self.assertEqual(len(state.stages), 3)
            self.assertEqual(state.stages[-1], STAGES[2])
            for _ in state.stages:
                self.assertEqual(state.result, '')
                state.advance()
            self.assertEqual(state.result, REJECTION)

    def test_early_stages_never_reject(self):
        state = SimulatorState()
        for _ in range(2):
            self.assertEqual(state.result, '')
            state.advance()
        self.assertEqual(state.result, '')
        self.assertFalse(state.finished)

    def test_final_stage_only_rejects_on_finish(self):
        state = SimulatorState()
        for _ in range(3): state.advance()
        self.assertEqual(state.result, REJECTION)
        self.assertTrue(state.finished)

    def test_exit_preserves_progress(self):
        state = SimulatorState(); state.advance(); state.exit()
        self.assertEqual(state.step, 1)
        self.assertTrue(state.exited)
        self.assertEqual(state.result, '')

    def test_finished_progress_is_retained_and_repeat_is_idempotent(self):
        state = SimulatorState()
        for _ in range(3): state.advance()
        state.exit(); state.advance()
        self.assertTrue(state.finished)
        self.assertEqual(state.step, 2)
        self.assertEqual(state.result, REJECTION)

    def test_real_importer_accepts_valid_case_after_demo(self):
        state = SimulatorState()
        for _ in range(3): state.advance()
        path = Path(__file__).resolve().parents[1] / 'docs/red_tape/examples/case.json'
        case = strict_load(path)
        self.assertEqual(validate(case)['id'], case['id'])
        with tempfile.TemporaryDirectory() as directory:
            tabbed = Path(directory) / 'synthetic-tabbed-case.json'
            tabbed.write_text(json.dumps(case, indent='\t'), encoding='utf-8')
            self.assertEqual(validate(strict_load(tabbed))['id'], case['id'])
        self.assertEqual(json.loads(STAGES[2][1])['fictional_form'], 'RT-418')
