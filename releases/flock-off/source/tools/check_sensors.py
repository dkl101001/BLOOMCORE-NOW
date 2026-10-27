"""Exercise real Tk callbacks and a worker-owned sensor session using synthetic input."""
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import tkinter as tk
from flockoff.sensor_desktop import SensorConsole
from flockoff.sensor_session import verify_session


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = tk.Tk(); root.withdraw()
        app = SensorConsole(root)
        try:
            app.fixture(); root.update()
            assert app.fields['mode'].get() == 'REPLAY'
            assert app.check()['ready']
            output = Path(temporary) / 'session'
            key = Path(temporary) / 'external.key'
            app.launch(app.config(), output, key)
            deadline = time.monotonic() + 30
            while app.worker is not None and time.monotonic() < deadline:
                root.update(); time.sleep(0.02)
            assert app.worker is None, 'worker did not complete'
            receipt = json.loads((output / 'receipt.json').read_text())
            assert receipt['status'] == 'COMPLETED', receipt
            assert receipt['stored_nodes'] > 0
            assert 'REPLAY' in app.banner.get()
            assert 'NOT RUN' in app.banner.get()
            assert verify_session(output, key)['state'] == 'VERIFIED_BYTES'
            assert 'match state: MATCH' in app.log.get('1.0', 'end')
            assert all(str(widget.cget('state')) == normal for widget, normal in app.controls)
            print('PASS: native sensor forms, synthetic fixture, background worker, candidate matches, persisted node, receipt verification, controls restored')
        finally:
            app.stop.set()
            if app.worker: app.worker.join(5)
            app.close()


if __name__ == '__main__': main()
