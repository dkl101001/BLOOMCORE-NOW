"""Local sensor console; worker owns its SQLite connection, UI stays responsive."""
import json
import queue
import threading
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .sensor_session import SessionConfig, preflight, run_session, verify_session
from .sensor_transport import list_ports


class SensorConsole:
    def __init__(self, root):
        self.root = root
        self.worker = None
        self.stop = threading.Event()
        self.messages = queue.Queue(maxsize=512)
        self.last_session = None
        self.last_key = None
        self.closed = False
        self.rendered_lines = 0
        root.title('FLOCK OFF • Sensor Console')
        root.geometry('1150x900')
        root.minsize(920, 780)
        root.protocol('WM_DELETE_WINDOW', self.close)
        style = ttk.Style(root); style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10))
        body = ttk.Frame(root, padding=16); body.pack(fill='both', expand=True)
        ttk.Label(body, text='FLOCK OFF / Sensor console', font=('Segoe UI', 23, 'bold')).pack(anchor='w')
        ttk.Label(body, text='Read-only host ingestion • Private evidence • Radio hardware validation: NOT RUN').pack(anchor='w', pady=8)
        self.fields = {}
        grid = ttk.Frame(body); grid.pack(fill='x')
        grid.columnconfigure(1, weight=1)
        definitions = [
            ('mode', 'Mode', ['REPLAY', 'LIVE_SERIAL'], 'REPLAY'),
            ('protocol', 'Decoded protocol', ['flock_you', 'remote_id'], 'flock_you'),
            ('sensor_input', 'Sensor file or serial:COM3', None, ''),
            ('pose_input', 'Optional pose NDJSON file / serial port', None, ''),
            ('receiver_id', 'Receiver ID', None, 'rx-1'),
            ('receiver_build', 'Actual receiver firmware / build', None, ''),
            ('core_build', 'Remote ID decoder build', None, ''),
            ('baud', 'Sensor baud', None, '115200'),
            ('pose_baud', 'Pose baud (decoded NDJSON, not raw NMEA)', None, '9600'),
            ('signature', 'Flock-You signature JSON', None, ''),
            ('targets', 'Optional independently sourced targets JSON', None, ''),
            ('max_records', 'Maximum input records per session', None, '10000'),
            ('max_seconds', 'Maximum session duration (seconds)', None, '3600'),
        ]
        self.controls = []
        for index, (key, label, values, default) in enumerate(definitions):
            ttk.Label(grid, text=label).grid(row=index, column=0, sticky='w', padx=(0, 12), pady=3)
            variable = tk.StringVar(value=default)
            widget = ttk.Combobox(grid, values=values, state='readonly', textvariable=variable) if values else ttk.Entry(grid, textvariable=variable)
            widget.grid(row=index, column=1, sticky='ew', pady=3)
            self.fields[key] = variable
            self.controls.append((widget, 'readonly' if values else 'normal'))
            if key in ('sensor_input', 'pose_input', 'signature', 'targets'):
                button = ttk.Button(grid, text='Browse', command=lambda k=key: self.browse(k))
                button.grid(row=index, column=2, padx=6)
                self.controls.append((button, 'normal'))
        toolbar = ttk.Frame(body); toolbar.pack(fill='x', pady=12)
        for label, action in [('List serial devices', self.devices), ('Preflight', self.check),
                              ('Load synthetic fixture', self.fixture), ('Start session', self.start)]:
            button = ttk.Button(toolbar, text=label, command=lambda a=action: self.safe(a))
            button.pack(side='left', padx=(0, 6)); self.controls.append((button, 'normal'))
        ttk.Button(toolbar, text='Stop', command=self.stop.set).pack(side='left', padx=6)
        ttk.Button(toolbar, text='Verify saved session', command=lambda: self.safe(self.verify)).pack(side='left')
        self.banner = tk.StringVar(value='IDLE — choose replay files or configure an actual receiver.')
        ttk.Label(body, textvariable=self.banner, font=('Segoe UI', 12, 'bold'), wraplength=1000).pack(anchor='w', pady=8)
        panel = ttk.Frame(body); panel.pack(fill='both', expand=True)
        self.log = tk.Text(panel, wrap='word', font=('Consolas', 10), state='disabled', padx=10, pady=10)
        scrollbar = ttk.Scrollbar(panel, command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y'); self.log.pack(fill='both', expand=True)
        ttk.Label(body, text='No complete records ≠ no transmitter. A candidate match does not identify an owner or prove surveillance.\nPose coordinates stay in the restricted vault. Keep the separate session key for recovery.', wraplength=1050).pack(anchor='w', pady=10)
        self.timer = root.after(100, self.poll)

    def safe(self, action):
        try: action()
        except Exception as exc: messagebox.showerror('Sensor console', str(exc), parent=self.root)

    def browse(self, key):
        path = filedialog.askopenfilename(title='Select local input')
        if path: self.fields[key].set(path)

    def config(self):
        values = {k: v.get().strip() for k, v in self.fields.items()}
        values['baud'] = int(values['baud']); values['pose_baud'] = int(values['pose_baud'])
        values['max_records'] = int(values['max_records']); values['max_seconds'] = int(values['max_seconds'])
        return SessionConfig(**values)

    def write(self, text):
        self.log.configure(state='normal'); self.log.insert('end', text + '\n')
        self.rendered_lines += 1
        if self.rendered_lines > 600:
            self.log.delete('1.0', '101.0'); self.rendered_lines -= 100
        self.log.see('end'); self.log.configure(state='disabled')

    def devices(self):
        found = list_ports()
        if not found['serial_dependency']:
            self.write('Serial support missing. Install the optional pyserial dependency in this Python environment.')
        elif not found['ports']:
            self.write('No serial devices found. No radio has been opened or tested.')
        for port in found['ports']:
            self.write(f"{port['device']}: {port['description']} (USB VID={port['vid']}, PID={port['pid']})")

    def check(self):
        report = preflight(self.config())
        self.write('PREFLIGHT: ' + ('CONFIGURATION ACCEPTED' if report['ready'] else 'BLOCKED'))
        for error in report['errors']: self.write('ERROR: ' + error)
        for note in report['notes']: self.write(note)
        return report

    def fixture(self):
        root = Path(__file__).resolve().parents[2]
        if not (root / 'TESTS/synthetic_traces/fixed_two_pass.jsonl').is_file():
            raise ValueError('Synthetic fixture loading is available in the source checkout.')
        directory = root / 'work' / ('synthetic-input-' + uuid.uuid4().hex[:8])
        directory.mkdir(parents=True)
        sensor, pose = [], []
        for line in (root / 'TESTS/synthetic_traces/fixed_two_pass.jsonl').read_text().splitlines():
            record = json.loads(line)
            if record['kind'] == 'pose':
                pose.append(record)
            else:
                sensor.append({'received_at_utc': record['observed_at_utc'], 'payload': record['payload']})
        # Retain pass IDs from the fixture's explicit observation-to-pose mapping.
        original = [json.loads(line) for line in (root / 'TESTS/synthetic_traces/fixed_two_pass.jsonl').read_text().splitlines()]
        pass_for = {row['pose_alias']: row['pass_id'] for row in original if row['kind'] != 'pose'}
        for row in pose: row['pass_id'] = pass_for[row['alias']]
        for name, rows in [('sensor.ndjson', sensor), ('pose.ndjson', pose)]:
            (directory / name).write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
        values = {'mode': 'REPLAY', 'protocol': 'flock_you', 'receiver_id': pose[0]['receiver_id'],
                  'receiver_build': 'SYNTHETIC_FIXTURE_NOT_HARDWARE', 'core_build': '',
                  'sensor_input': str(directory / 'sensor.ndjson'), 'pose_input': str(directory / 'pose.ndjson'),
                  'signature': str(root / 'SIGNATURES/candidate/flock_you_wifi_assertion_v0.1.0.json'), 'targets': ''}
        for key, value in values.items(): self.fields[key].set(value)
        self.banner.set('REPLAY CONFIGURED — synthetic fixture, no radio reception.')
        self.write('Synthetic inputs loaded. Start creates a real private ledger from test input; it does not validate hardware.')

    def start(self):
        if self.worker and self.worker.is_alive(): raise ValueError('A session is already running.')
        report = self.check()
        if not report['ready']: return
        parent = filedialog.askdirectory(title='Private parent folder for a new sensor session')
        if not parent: return
        key = filedialog.asksaveasfilename(title='New external session key — keep outside the session folder', defaultextension='.key')
        if not key: return
        output = Path(parent) / ('sensor-session-' + uuid.uuid4().hex[:12])
        self.launch(self.config(), output, Path(key))

    def launch(self, config, output, key):
        if self.worker and self.worker.is_alive(): raise ValueError('Session already running')
        self.stop = threading.Event()
        self.last_session, self.last_key = output, key
        for widget, _ in self.controls: widget.configure(state='disabled')
        self.banner.set(config.mode + ' — STARTING (hardware validation NOT RUN)')
        def emit(item):
            try: self.messages.put_nowait(item)
            except queue.Full: pass  # UI preview only; durable event log is written first.
        def work():
            try:
                receipt = run_session(config, output, key, stop=self.stop, notify=emit)
                emit({'kind': 'result', 'status': receipt['status'], 'counts': receipt['counts']})
            except Exception as exc:
                emit({'kind': 'startup_failure', 'reason': str(exc)})
        self.worker = threading.Thread(target=work, daemon=True, name='sensor-session')
        self.worker.start()

    def poll(self):
        if self.closed: return
        for _ in range(150):
            try: item = self.messages.get_nowait()
            except queue.Empty: break
            if item['kind'] == 'evidence':
                detail = ' · '.join(f'{k.replace("_", " ")}: {v}' for k, v in item.get('summary', {}).items())
                self.write(item['evidence_kind'].replace('_', ' ').capitalize() + (': ' + detail if detail else ' retained'))
            elif item['kind'] == 'transport':
                self.write(f"{item['source']}: {item['state']} — {item.get('detail') or 'local serial connection'}")
            elif item['kind'] == 'quarantined':
                self.write(f"Rejected {item['source']} record: invalid input; no raw identifier retained in diagnostics.")
            else:
                self.write(item['kind'].replace('_', ' ').capitalize() + ': ' + str(item.get('status', item.get('reason', item.get('mode', '')))))
                if item['kind'] == 'session_finished':
                    counts = item.get('counts', {})
                    self.write(f"Input records: sensor {counts.get('sensor_records', 0)}, pose {counts.get('pose_records', 0)}; rejected {counts.get('quarantined', 0)}.")
            if item['kind'] in ('result', 'session_finished', 'startup_failure'):
                self.banner.set(item.get('status', 'STARTUP FAILED') + ' — hardware validation NOT RUN')
        if self.worker and not self.worker.is_alive():
            self.worker = None
            for widget, normal in self.controls: widget.configure(state=normal)
            if self.last_session and (self.last_session / 'receipt.json').exists():
                receipt = json.loads((self.last_session / 'receipt.json').read_text())
                self.banner.set(receipt['mode'] + ': ' + receipt['status'] + ' — hardware validation NOT RUN')
                self.write('Saved: ' + str(self.last_session))
        self.timer = self.root.after(100, self.poll)

    def verify(self):
        directory = filedialog.askdirectory(title='Choose a completed session folder')
        if not directory: return
        key = filedialog.askopenfilename(title='Choose the matching external session key')
        if key: self.write(json.dumps(verify_session(directory, key)))

    def close(self):
        if self.worker and self.worker.is_alive():
            self.stop.set()
            self.banner.set('STOPPING — waiting for the reader and ledger to close safely…')
            self.root.after(200, self.close)
            return
        self.closed = True
        self.root.after_cancel(self.timer)
        self.root.destroy()


def main():
    root = tk.Tk(); SensorConsole(root); root.mainloop()


if __name__ == '__main__': main()
