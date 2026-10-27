# SPDX-License-Identifier: Apache-2.0
"""Native, offline records desk. No HTTP server or browser storage."""
import copy
import os
import uuid
from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .hounds import Hounds
from .simulator import SimulatorState, SimulatorWindow
from .workspace_ui import launch_workspace_paths
from .research_ui import launch_research
from .cli import strict_load
from .desk import Desk, new_case, now
from .ledger import private_write
from .model import REVIEW_CHECKS, ASSESSMENT_STATES, REQUEST_STATES, STATUSES
from .render import ASSESSMENT, brief, request_draft


# Field type: text, paragraph, date, number, boolean, references, or choices.
SOURCE = [('id', 'Source ID', 'text'), ('title', 'Document title', 'text'),
          ('issuer', 'Issuing body', 'text'), ('document_date', 'Document date (YYYY-MM-DD)', 'text'),
          ('retrieved_at', 'Retrieved at (timestamp with timezone)', 'text'),
          ('url', 'Original public URL', 'text'), ('locator', 'Exact page / section', 'text'),
          ('content', 'Excerpt or paraphrase', 'paragraph'),
          ('content_kind', 'Content kind', ['excerpt', 'paraphrase']),
          ('limits', 'What this record does not establish', 'paragraph'),
          ('parent_id', 'Copied from source ID (optional)', 'optional'),
          ('superseded_by', 'Superseded by source ID (optional)', 'optional')]
CLAIM = [('id', 'Claim ID', 'text'), ('text', 'Factual premise or open question', 'paragraph'),
         ('basis', 'Basis', ['document', 'attributed_statement', 'inference', 'open_question']),
         ('evidence_ids', 'Supporting source IDs (comma separated)', 'references'),
         ('contrary_ids', 'Contrary source IDs (comma separated)', 'references'),
         ('qualification', 'Qualification', 'paragraph'),
         ('disposition', 'Disposition', ['unverified', 'supported', 'partial', 'disputed', 'corrected', 'withdrawn'])]
QUESTION = [('id', 'Question ID', 'text'), ('subject', 'Subject', 'text'),
            ('text', 'Question', 'paragraph'), ('claim_ids', 'Premise IDs (comma separated)', 'references'),
            ('gap', 'Unresolved gap', 'paragraph'), ('follow_up', 'Clarification', 'paragraph'),
            ('rank_reason', 'Why this question comes first', 'text'), ('priority', 'Priority (1–100)', 'number')]
ANSWER = [('id', 'Answer ID (new ID for a correction)', 'text'), ('question_id', 'Question ID', 'text'),
          ('kind', 'Record kind', ['note', 'paraphrase', 'quote']), ('text', 'Recorded answer', 'paragraph'),
          ('context', 'Meeting / context', 'text'), ('speaker_role', 'Speaker / role', 'text'),
          ('source', 'Where this answer was recorded', 'text'), ('locator', 'Timestamp / page', 'text'),
          ('recorded_at', 'Recorded at (timestamp with timezone)', 'text'),
          ('status', 'Human-assessed status', sorted(STATUSES)), ('reviewer', 'Recorded by', 'text'),
          ('remaining_gap', 'Remaining gap', 'paragraph'),
          ('corroboration', 'Corroboration', ['attributed_only', 'document_supported', 'disputed']),
          ('evidence_ids', 'Source IDs (comma separated)', 'references'),
          ('quote_verified', 'I checked this quotation against its source', 'boolean')]
REQUEST = [('id', 'Request ID', 'text'), ('scope', 'Bounded scope', 'paragraph'),
           ('start_date', 'Period start (YYYY-MM-DD)', 'text'), ('end_date', 'Period end', 'text'),
           ('categories', 'Record categories (one per line)', 'lines'),
           ('recipient_url', 'Verified official submission channel URL', 'text'),
           ('recipient_verified_at', 'Channel verified on (YYYY-MM-DD)', 'text'),
           ('fee_ceiling', 'Fee ceiling', 'text'), ('status', 'Request status', sorted(REQUEST_STATES)),
           ('existing_evidence_ids', 'Existing source IDs (comma separated)', 'references'),
           ('remaining_gap', 'Remaining question', 'paragraph'),
           ('sent_at', 'Actual sent date (optional)', 'optional'),
           ('reference', 'Submission reference (optional)', 'optional'),
           ('next_review_date', 'Next review date (optional)', 'optional')]


class Form(tk.Toplevel):
    def __init__(self, parent, title, fields, initial, submit):
        super().__init__(parent)
        self.title(title)
        self.geometry('780x760')
        self.transient(parent)
        self.grab_set()
        self.initial, self.submit, self.widgets = copy.deepcopy(initial), submit, []
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill='both', expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        canvas.pack(fill='both', expand=True)
        body = ttk.Frame(canvas, padding=8)
        window = canvas.create_window((0, 0), window=body, anchor='nw')
        body.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(window, width=e.width))
        body.columnconfigure(0, weight=1)
        for index, (key, label, kind) in enumerate(fields):
            value = initial.get(key, False if kind == 'boolean' else '')
            ttk.Label(body, text=label).grid(row=index * 2, column=0, sticky='w', pady=(8, 2))
            if kind == 'boolean':
                variable = tk.BooleanVar(value=bool(value))
                widget = ttk.Checkbutton(body, text='Yes — explicitly confirmed', variable=variable)
                getter = variable.get
            elif kind in ('paragraph', 'lines'):
                widget = tk.Text(body, height=3, wrap='word', font=('Segoe UI', 10), undo=True)
                widget.insert('1.0', '\n'.join(value) if kind == 'lines' else value)
                getter = lambda w=widget: w.get('1.0', 'end-1c').strip()
            else:
                if isinstance(kind, list):
                    widget = ttk.Combobox(body, values=kind, state='readonly')
                    widget.set(value or kind[0])
                else:
                    widget = ttk.Entry(body)
                    widget.insert(0, ', '.join(value) if kind == 'references' else str(value))
                getter = widget.get
            widget.grid(row=index * 2 + 1, column=0, sticky='ew')
            self.widgets.append((key, kind, getter))
        footer = ttk.Frame(self, padding=12)
        footer.pack(fill='x')
        ttk.Button(footer, text='Cancel', command=self.destroy).pack(side='right', padx=6)
        ttk.Button(footer, text='Save', command=self.save).pack(side='right')

    def save(self):
        try:
            result = copy.deepcopy(self.initial)
            for key, kind, getter in self.widgets:
                value = getter()
                if kind == 'number':
                    value = int(value)
                elif kind == 'references':
                    value = [s.strip() for s in value.split(',') if s.strip()]
                elif kind == 'lines':
                    value = [s.strip() for s in value.splitlines() if s.strip()]
                elif kind == 'optional' and not value.strip():
                    result.pop(key, None)
                    continue
                result[key] = value
            self.submit(result)
            self.destroy()
        except Exception as exc:
            messagebox.showerror('Could not save — your entries are still here', str(exc), parent=self)


class App:
    def __init__(self, root):
        self.root, self.desk, self.case, self.receipt = root, None, None, None
        self.hounds = Hounds()
        self.simulator_state = SimulatorState()
        self.simulator_window = None
        root.title('FLOCK OFF • Red Tape Records Desk')
        root.geometry('1220x840')
        root.minsize(900, 650)
        root.protocol('WM_DELETE_WINDOW', self.close)
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10))
        style.configure('TButton', padding=(10, 7))
        style.configure('Heading.TLabel', font=('Segoe UI', 22, 'bold'))
        top = ttk.Frame(root, padding=16)
        top.pack(fill='x')
        ttk.Label(top, text='RED TAPE / Records desk', style='Heading.TLabel').pack(anchor='w')
        ttk.Label(top, text='Original records → supported questions → reviewed packets → accountable follow-up').pack(anchor='w', pady=5)
        self.hounds_message = tk.StringVar(value='')
        ttk.Button(top, text='Private notes / Shared room / Council packet', command=lambda: launch_workspace_paths(self.root)).pack(anchor='w')
        ttk.Button(top, text='Public records research (off until enabled)', command=lambda: launch_research(self.root)).pack(anchor='w')
        self.hounds_button = ttk.Button(top, text='Release the Hounds (sound)', takefocus=True, command=self.release_hounds)
        self.hounds_button.pack(anchor='w')
        ttk.Button(top, text='Bureaucracy Simulator (satire demo)', takefocus=True,
                   command=self.open_simulator).pack(anchor='w')
        ttk.Label(top, textvariable=self.hounds_message, wraplength=850).pack(anchor='w')
        toolbar = ttk.Frame(root, padding=(16, 0, 16, 8))
        toolbar.pack(fill='x')
        for label, action in [('New workspace', self.create_workspace), ('Open workspace', self.open_workspace),
                              ('New case', self.create_case), ('Import case', self.import_case),
                              ('Backup', self.backup), ('Sensor console', self.sensors)]:
            ttk.Button(toolbar, text=label, command=lambda a=action: self.run(a)).pack(side='left', padx=(0, 6))
        self.location = ttk.Label(root, text='Open an existing database and its key, or create a new workspace.', padding=(16, 6))
        self.location.pack(fill='x')
        panes = ttk.Panedwindow(root, orient='horizontal')
        panes.pack(fill='both', expand=True, padx=16, pady=8)
        left = ttk.Frame(panes)
        self.cases = ttk.Treeview(left, columns=('agency',), show='tree headings', selectmode='browse')
        self.cases.heading('#0', text='Case ID')
        self.cases.heading('agency', text='Agency')
        self.cases.column('#0', width=130)
        self.cases.column('agency', width=150)
        self.cases.pack(fill='both', expand=True)
        self.cases.bind('<<TreeviewSelect>>', lambda e: self.run(self.select_case))
        panes.add(left, weight=1)
        right = ttk.Frame(panes)
        panes.add(right, weight=4)
        self.heading = ttk.Label(right, text='No case selected', font=('Segoe UI', 15, 'bold'))
        self.heading.pack(anchor='w', pady=8)
        self.tabs = ttk.Notebook(right)
        self.tabs.pack(fill='both', expand=True)
        overview = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(overview, text='Overview')
        actions = ttk.Frame(overview)
        actions.pack(fill='x')
        for label, action in [('Edit case', self.edit_case), ('Select questions', self.select_questions),
                              ('Meeting rules', self.meeting_rules), ('Review', self.review)]:
            ttk.Button(actions, text=label, command=lambda a=action: self.run(a)).pack(side='left', padx=3)
        self.summary = tk.Text(overview, wrap='word', font=('Segoe UI', 11), padx=12, pady=12)
        self.summary.pack(fill='both', expand=True, pady=8)
        self.tables = {}
        for kind, title in [('sources', 'Evidence'), ('claims', 'Premises'), ('questions', 'Questions'),
                            ('answers', 'Answers'), ('assessment', 'Assessment'), ('requests', 'Requests')]:
            page = ttk.Frame(self.tabs, padding=10)
            self.tabs.add(page, text=title)
            bar = ttk.Frame(page)
            bar.pack(fill='x')
            ttk.Button(bar, text='View selected', command=lambda k=kind: self.run(lambda: self.view_record(k))).pack(side='left', padx=3)
            if kind != 'assessment':
                ttk.Button(bar, text='Add', command=lambda k=kind: self.run(lambda: self.edit_record(k, True))).pack(side='left', padx=3)
            if kind != 'answers':
                ttk.Button(bar, text='Edit selected', command=lambda k=kind: self.run(lambda: self.edit_record(k))).pack(side='left', padx=3)
            if kind == 'sources':
                ttk.Button(bar, text='Attach original', command=lambda: self.run(self.attach)).pack(side='left', padx=3)
                ttk.Button(bar, text='Save original copy', command=lambda: self.run(self.document)).pack(side='left', padx=3)
            if kind == 'requests':
                ttk.Button(bar, text='Draft request', command=lambda: self.run(self.request)).pack(side='left', padx=3)
                ttk.Button(bar, text='Draft follow-up', command=lambda: self.run(lambda: self.request(True))).pack(side='left', padx=3)
            if kind == 'answers':
                ttk.Label(bar, text='History is permanent. Append a new answer to record a correction.').pack(side='left')
            tree = ttk.Treeview(page, columns=('description', 'state'), show='tree headings', selectmode='browse')
            tree.heading('#0', text='ID'); tree.heading('description', text='Record'); tree.heading('state', text='Status')
            tree.column('#0', width=65, stretch=False); tree.column('description', width=390); tree.column('state', width=120)
            tree.pack(fill='both', expand=True, pady=8)
            self.tables[kind] = tree
        output = ttk.Frame(right)
        output.pack(fill='x', pady=8)
        for label, action in [('Generate draft', lambda: self.generate(False)),
                              ('Generate reviewed packet', lambda: self.generate(True)),
                              ('Verify packet', self.verify_packet), ('Verify history', self.verify_history)]:
            ttk.Button(output, text=label, command=lambda a=action: self.run(a)).pack(side='left', padx=3)
        self.status = tk.StringVar(value='Local desktop • No automatic sending or publishing • v0.2 candidate')
        ttk.Label(root, textvariable=self.status, padding=12).pack(fill='x')

    def run(self, action):
        try:
            action()
        except Exception as exc:
            messagebox.showerror('Action could not complete', str(exc), parent=self.root)

    def sensors(self):
        from flockoff.sensor_desktop import SensorConsole
        SensorConsole(tk.Toplevel(self.root))

    def require(self, case=True):
        if self.desk is None:
            raise ValueError('Create or open a workspace first.')
        if case and self.case is None:
            raise ValueError('Select a case first.')

    def use(self, db, key, create=False):
        desk = Desk(db, key, create)
        try:
            desk.cases()  # Fail before replacing the current workspace on wrong key/corruption.
        except Exception:
            desk.close()
            raise
        if self.desk:
            self.desk.close()
        self.desk, self.case, self.receipt = desk, None, None
        self.location.configure(text=f'Encrypted store: {db}  |  Key is stored separately. Back up both separately.')
        self.refresh()

    def create_workspace(self):
        db = filedialog.asksaveasfilename(title='New database — choose a private local folder', defaultextension='.sqlite', filetypes=[('SQLite', '*.sqlite')])
        if not db: return
        key = filedialog.asksaveasfilename(title='New encryption key — keep a separate secure backup', defaultextension='.key', filetypes=[('Encryption key', '*.key')])
        if key: self.use(db, key, True)

    def open_workspace(self):
        db = filedialog.askopenfilename(title='Open accountability database', filetypes=[('SQLite', '*.sqlite'), ('All files', '*')])
        if not db: return
        key = filedialog.askopenfilename(title='Select the matching external encryption key', filetypes=[('Key', '*.key'), ('All files', '*')])
        if key: self.use(db, key)

    def refresh(self, case_id=None):
        for item in self.cases.get_children(): self.cases.delete(item)
        for case, receipt in self.desk.cases():
            self.cases.insert('', 'end', iid=case['id'], text=case['id'], values=(case['agency'],))
        if case_id:
            self.cases.selection_set(case_id)
            self.select_case()
        else:
            self.heading.configure(text='Select a case or create one')
            for tree in self.tables.values():
                for item in tree.get_children(): tree.delete(item)
            self.summary.configure(state='normal'); self.summary.delete('1.0', 'end'); self.summary.configure(state='disabled')

    def select_case(self):
        selected = self.cases.selection()
        if not selected: return
        self.case, self.receipt = self.desk.store.load(selected[0])
        self.heading.configure(text=f"{self.case['agency']} · revision {self.receipt['revision']}")
        status = self.desk.status(self.case)
        text = brief(self.case) + '\nREVIEW\n' + '\n'.join(status['errors'] or ['Human review recorded. Check timing before use.'])
        text += '\n\nREADING BUDGET\n' + str(status['timing'])
        text += '\n\nREQUEST REMINDERS\n'
        for request in status['tracker']['requests']:
            text += f"{request['id']}: {request.get('status', '')} | review due: {request.get('review_due', False)}\n"
        self.summary.configure(state='normal'); self.summary.delete('1.0', 'end'); self.summary.insert('1.0', text); self.summary.configure(state='disabled')
        for kind, tree in self.tables.items():
            for item in tree.get_children(): tree.delete(item)
            rows = self.case[kind]
            if kind == 'assessment':
                for tid, title, question in ASSESSMENT:
                    tree.insert('', 'end', iid=tid, text=tid, values=(title + ': ' + question, rows[tid]['state']))
            else:
                for row in rows:
                    description = row.get('title', row.get('text', row.get('scope', '')))
                    state = row.get('status', row.get('disposition', ''))
                    if kind == 'sources':
                        sha = row.get('sha256')
                        held = sha and self.desk.store.db.execute('SELECT 1 FROM documents WHERE sha256=?', (sha,)).fetchone()
                        state = 'Original retained' if held else 'Metadata only'
                    tree.insert('', 'end', iid=row['id'], text=row['id'], values=(description.replace('\n', ' '), state))

    def save(self, case):
        receipt = self.desk.save(case, self.receipt['revision'])
        self.refresh(case['id'])
        self.status.set(f"Saved revision {receipt['revision']}. Content edits require a fresh review.")

    def create_case(self):
        self.require(False)
        fields = [(k, label, 'paragraph' if k in ('action', 'why', 'question', 'qualification') else 'text') for k, label in [
            ('case_id', 'Opaque case ID'), ('agency', 'Agency / public body'), ('meeting_date', 'Meeting date (YYYY-MM-DD)'),
            ('agenda', 'Agenda item'), ('decision', 'Decision under consideration'), ('agenda_url', 'Official agenda URL'),
            ('action', 'Requested action'), ('why', 'Why this matters — qualify any unverified premise'),
            ('question', 'First question'), ('qualification', 'Material limits and uncertainties')]]
        def submit(values):
            case = new_case(**values)
            self.desk.save(case, 0)
            self.refresh(case['id'])
        Form(self.root, 'Create a real case — no sample facts are inserted', fields,
             {'case_id': 'case-' + uuid.uuid4().hex[:10], 'meeting_date': date.today().isoformat()}, submit)

    def import_case(self):
        self.require(False)
        path = filedialog.askopenfilename(title='Import a new case (existing IDs are refused)', filetypes=[('Case JSON', '*.json')])
        if path:
            case = strict_load(path)
            self.desk.save(case, 0)
            self.refresh(case['id'])

    def edit_case(self):
        self.require()
        case = copy.deepcopy(self.case)
        fields = [('agency', 'Agency', 'text'), ('requested_action', 'Requested action', 'paragraph'),
                  ('why_text', 'Why this matters', 'paragraph'), ('why_claims', 'Supporting premise IDs', 'references'),
                  ('qualification', 'Material qualification', 'paragraph'),
                  ('date', 'Meeting date', 'text'), ('agenda_item', 'Agenda item', 'text'),
                  ('decision', 'Decision', 'text'), ('url', 'Agenda URL', 'text')]
        initial = {**case['meeting'], 'agency': case['agency'], 'requested_action': case['requested_action'],
                   'why_text': case['why']['text'], 'why_claims': case['why']['claim_ids'], 'qualification': case['qualification']}
        def submit(v):
            for k in ('agency', 'requested_action', 'qualification'): case[k] = v[k]
            case['why'] = {'text': v['why_text'], 'claim_ids': v['why_claims']}
            for k in ('date', 'agenda_item', 'decision', 'url'): case['meeting'][k] = v[k]
            self.save(case)
        Form(self.root, 'Case details', fields, initial, submit)

    def selected_id(self, kind):
        self.require()
        selection = self.tables[kind].selection()
        if not selection: raise ValueError('Select a record first.')
        return selection[0]

    def edit_record(self, kind, add=False):
        self.require()
        case = copy.deepcopy(self.case)
        if kind == 'assessment':
            tid = self.selected_id(kind)
            fields = [('state', 'Assessment state', sorted(ASSESSMENT_STATES)),
                      ('evidence_ids', 'Source IDs', 'references'), ('explanation', 'Reason and limits', 'paragraph')]
            def submit(v):
                case[kind][tid] = v
                self.save(case)
            Form(self.root, dict((x[0], x[2]) for x in ASSESSMENT)[tid], fields, case[kind][tid], submit)
            return
        specs = {'sources': SOURCE, 'claims': CLAIM, 'questions': QUESTION, 'answers': ANSWER, 'requests': REQUEST}
        fields = specs[kind]
        if add:
            initial = {k: [] for k, _, t in fields if t in ('references', 'lines')}
            initial.update(id={'sources': 'E', 'claims': 'C', 'questions': 'Q', 'answers': 'A', 'requests': 'R'}[kind] + uuid.uuid4().hex[:6])
            if kind == 'sources': initial.update(retrieved_at=now(), content_kind='paraphrase')
            if kind == 'questions': initial.update(priority=1)
            if kind == 'answers': initial.update(recorded_at=now(), status='unanswered', kind='note')
            if kind == 'requests': initial.update(status='draft')
        else:
            rid = self.selected_id(kind)
            initial = next(x for x in case[kind] if x['id'] == rid)
            fields = [f for f in fields if f[0] != 'id']
        def submit(value):
            candidate = copy.deepcopy(case)
            if add: candidate[kind].append(value)
            else: candidate[kind] = [value if x['id'] == value['id'] else x for x in candidate[kind]]
            self.save(candidate)
        Form(self.root, ('Add ' if add else 'Edit ') + kind, fields, initial, submit)

    def view_record(self, kind):
        rid = self.selected_id(kind)
        row = self.case[kind][rid] if kind == 'assessment' else next(x for x in self.case[kind] if x['id'] == rid)
        window = tk.Toplevel(self.root)
        window.title(f'{rid} — retained record')
        window.geometry('760x640')
        view = tk.Text(window, wrap='word', padx=16, pady=16, font=('Segoe UI', 11))
        scroll = ttk.Scrollbar(window, command=view.yview)
        view.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y'); view.pack(fill='both', expand=True)
        def describe(value, indent=''):
            if isinstance(value, dict):
                return '\n'.join(indent + k.replace('_', ' ').capitalize() + ':\n' + describe(v, indent + '  ') for k, v in value.items())
            if isinstance(value, list):
                return '\n'.join(describe(v, indent) for v in value) or indent + '(none)'
            return indent + str(value) + '\n'
        view.insert('1.0', describe(row)); view.configure(state='disabled')

    def select_questions(self):
        self.require()
        case = copy.deepcopy(self.case)
        def submit(v):
            case['selected_questions'] = v['ids']; self.save(case)
        Form(self.root, 'Select one to three question IDs', [('ids', 'Selected question IDs in this case', 'references')],
             {'ids': case['selected_questions']}, submit)

    def meeting_rules(self):
        self.require(); case = copy.deepcopy(self.case)
        def submit(v):
            m = case['meeting']
            m.pop('speaking_seconds', None); m.pop('rules_url', None)
            m['rules_verified'] = v['verified']
            if v.get('url'): m['rules_url'] = v['url']
            if v.get('seconds'): m['speaking_seconds'] = int(v['seconds'])
            self.save(case)
        Form(self.root, 'Meeting rules — leave allowance blank for untimed drafts',
             [('url', 'Rules URL', 'optional'), ('seconds', 'Speaking allowance in seconds', 'optional'),
              ('verified', 'I checked the current meeting rules', 'boolean')],
             {'url': case['meeting'].get('rules_url', ''), 'seconds': str(case['meeting'].get('speaking_seconds', '')),
              'verified': False}, submit)

    def attach(self):
        sid = self.selected_id('sources')
        path = filedialog.askopenfilename(title='Retain original public document (maximum 20 MiB)')
        if path:
            self.desk.attach(self.case['id'], sid, path, self.receipt['revision'])
            self.refresh(self.case['id'])

    def document(self):
        sid = self.selected_id('sources')
        source = next(x for x in self.case['sources'] if x['id'] == sid)
        data = self.desk.store.read_document(source.get('sha256'))
        path = filedialog.asksaveasfilename(title='Save decrypted original — choose a private location')
        if path: private_write(path, data)

    def review(self):
        self.require(); cid, revision = self.case['id'], self.receipt['revision']
        fields = [('reviewer', 'Reviewer name', 'text')] + [(k, k.replace('_', ' ').capitalize(), 'boolean') for k in sorted(REVIEW_CHECKS)]
        def submit(v):
            self.desk.review(cid, revision, v['reviewer'], [k for k in REVIEW_CHECKS if v[k]])
            self.refresh(cid)
        Form(self.root, 'Record your review — attestations are never preselected', fields, {}, submit)

    def generate(self, ready):
        self.require()
        parent = filedialog.askdirectory(title='Parent folder for a new packet (contains plaintext drafts)')
        if not parent: return
        path = Path(parent) / ('packet-' + date.today().isoformat() + '-' + uuid.uuid4().hex[:8])
        self.desk.generate(self.case['id'], self.receipt['revision'], path, date.today().isoformat(), ready)
        self.status.set(f'Packet generated and reconstructed successfully: {path}')
        messagebox.showinfo('Packet saved and verified', f'{path}\n\nOpen town_hall.html to present or print. These files have not been published.', parent=self.root)

    def verify_packet(self):
        self.require()
        path = filedialog.askdirectory(title='Select a packet directory')
        if path:
            receipt = self.desk.verify_packet(self.case['id'], path)
            self.status.set(f"Packet matches its recorded revision {receipt['revision']} byte for byte.")

    def verify_history(self):
        self.require()
        count, _ = self.desk.store.verify(self.case['id'])
        self.status.set(f'{count} revisions verified. A separate backup checkpoint is needed to detect rollback to an older complete database.')

    def request(self, follow_up=False):
        rid = self.selected_id('requests')
        data = request_draft(self.case, rid, follow_up).encode()
        path = filedialog.asksaveasfilename(title='Save request draft — nothing will be sent', defaultextension='.txt')
        if path: private_write(path, data)

    def backup(self):
        self.require(False)
        parent = filedialog.askdirectory(title='Backup parent folder — encryption key will NOT be copied')
        if parent:
            path = self.desk.backup(Path(parent) / ('backup-' + date.today().isoformat() + '-' + uuid.uuid4().hex[:8]))
            messagebox.showinfo('Verified backup created', f'{path}\n\nBack up the external key separately. Restore by opening the backup database with that key.', parent=self.root)

    def release_hounds(self):
        self.hounds_message.set(self.hounds.release())

    def open_simulator(self):
        if self.simulator_window is not None and self.simulator_window.winfo_exists():
            self.simulator_window.lift()
        else:
            self.simulator_window = SimulatorWindow(self.root, self.simulator_state)

    def close(self):
        self.hounds.close()
        if self.desk: self.desk.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
