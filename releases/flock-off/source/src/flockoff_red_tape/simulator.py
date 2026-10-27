# SPDX-License-Identifier: Apache-2.0
"""Explicit satire with fixed synthetic inputs, isolated from real records."""
from dataclasses import dataclass, field
import random
import secrets
import tkinter as tk
from tkinter import ttk

STAGES = (
    ('Applicant', 'Applicant: The Department of Extremely Imaginary Forms'),
    ('Request', 'Request: Permission to request permission for a pretend rubber stamp'),
    ('JSON tab', '{\n\t"fictional_form": "RT-418",\n\t"rubber_stamps_requested": 1\n}'),
)
REJECTION = 'ERROR RT-418: INSUFFICIENT CEREMONIAL INDENTATION'
EXPLANATION = ('SATIRE ONLY: this indentation rule is fictional. Valid JSON tabs are not '
               'rejected by the real importer. Nothing was submitted or changed in your records.')


@dataclass
class SimulatorState:
    seed: int = field(default_factory=lambda: secrets.randbits(64))
    step: int = 0
    finished: bool = False
    exited: bool = False
    stages: tuple = field(init=False)

    def __post_init__(self):
        rng = random.Random(self.seed)
        departments = ['Imaginary Staplers', 'Ceremonial Paperclips', 'Unnecessary Countersignatures', 'Hypothetical Rubber Stamps']
        forms = ['Form of Forms', 'Permission to Request Permission', 'Duplicate Duplicate', 'Application for an Application']
        rng.shuffle(departments); rng.shuffle(forms)
        early = [(departments[i], f'SYNTHETIC: Department of {departments[i]}\nFictional form: {forms[i]}\nAction: acknowledge this entirely pointless demo stage.') for i in range(2)]
        rng.shuffle(early)
        self.stages = tuple(early) + (STAGES[2],)

    def advance(self):
        if self.finished:
            return
        self.exited = False
        if self.step < len(self.stages) - 1:
            self.step += 1
        else:
            self.finished = True

    def exit(self):
        self.exited = True  # Retain step and finish state for reopening this app session.

    @property
    def result(self):
        return REJECTION if self.finished else ''


class SimulatorWindow(tk.Toplevel):
    def __init__(self, parent, state):
        super().__init__(parent)
        self.state = state
        state.exited = False
        self.title('Bureaucracy Simulator — SATIRE / SYNTHETIC DEMO')
        self.geometry('720x470')
        self.protocol('WM_DELETE_WINDOW', self.leave)
        body = ttk.Frame(self, padding=18); body.pack(fill='both', expand=True)
        ttk.Label(body, text='BUREAUCRACY SIMULATOR — SATIRE', font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        ttk.Label(body, wraplength=660, text='Fixed fictional examples only. No real records, submissions, or validation are used. '
                  'You can exit at any time. Demo progress remains available until you close the records desk.').pack(anchor='w', pady=10)
        self.stage = tk.StringVar()
        ttk.Label(body, textvariable=self.stage).pack(anchor='w')
        self.content = tk.Text(body, height=7, wrap='word', takefocus=True)
        self.content.pack(fill='both', expand=True, pady=8)
        self.result = tk.StringVar()
        ttk.Label(body, textvariable=self.result, wraplength=660).pack(anchor='w', pady=8)
        actions = ttk.Frame(body); actions.pack(fill='x')
        self.next_button = ttk.Button(actions, command=self.advance, takefocus=True)
        self.next_button.pack(side='left')
        self.exit_button = ttk.Button(actions, text='Exit demo — keep progress', command=self.leave, takefocus=True)
        self.exit_button.pack(side='right')
        self.render()

    def render(self):
        self.stage.set(f'Step {self.state.step + 1} of {len(self.state.stages)} — {self.state.stages[self.state.step][0]}')
        self.content.configure(state='normal'); self.content.delete('1.0', 'end')
        self.content.insert('1.0', self.state.stages[self.state.step][1]); self.content.configure(state='disabled')
        self.result.set(self.state.result + '\n' + EXPLANATION if self.state.finished else 'Synthetic demonstration — no rejection yet.')
        self.next_button.configure(text='Demo finished' if self.state.finished else ('Finish demo' if self.state.step == 2 else 'Continue demo'),
                                   state='disabled' if self.state.finished else 'normal')

    def advance(self):
        self.state.advance(); self.render()

    def leave(self):
        self.state.exit(); self.destroy()
