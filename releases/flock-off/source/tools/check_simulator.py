# SPDX-License-Identifier: Apache-2.0
import sys
from pathlib import Path
import tkinter as tk
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from flockoff_red_tape.desktop import App
from flockoff_red_tape.simulator import REJECTION

root = tk.Tk(); root.withdraw(); app = App(root)
try:
    app.open_simulator(); demo = app.simulator_window; demo.withdraw(); root.update()
    assert not demo.grab_current()
    demo.next_button.invoke(); root.update()
    assert app.simulator_state.step == 1 and not app.simulator_state.result
    demo.exit_button.invoke(); root.update()
    app.open_simulator(); demo = app.simulator_window; demo.withdraw(); root.update()
    assert app.simulator_state.step == 1
    demo.next_button.invoke(); root.update()
    assert not app.simulator_state.result
    demo.next_button.invoke(); root.update()
    assert REJECTION in demo.result.get() and 'fictional' in demo.result.get()
    assert str(demo.next_button.cget('state')) == 'disabled'
    demo.exit_button.invoke(); root.update()
    app.open_simulator(); demo = app.simulator_window; demo.withdraw(); root.update()
    assert app.simulator_state.finished and REJECTION in demo.result.get()
    assert app.case is None and app.desk is None
    demo.leave()
finally:
    app.close()
print('PASS: nonmodal synthetic demo, end-only satire, exit/reopen retains progress, real workspace untouched')
