# SPDX-License-Identifier: Apache-2.0
import sys
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from flockoff_red_tape.workspace_ui import WorkspacePaths, OwnerConsole
root=tk.Tk();root.withdraw()
with patch('flockoff_collaboration.transport.Transport.rpc',side_effect=AssertionError('unexpected network')):
    app=WorkspacePaths(root);app.withdraw()
    try:
        root.update()
        assert not app.auto and not app.busy
        assert 'EXPERIMENTAL' in app.experimental_notice.cget('text')
        assert 'privacy is unvalidated' in app.experimental_notice.cget('text')
        assert not app.disclose.get()
        assert app.unbranded.get()
        assert not any(v.get() for v in app.scopes.values())
        assert app.peer_paths is None and app.notebook is None
        assert app.selected_text.get('1.0','end-1c') == ''
        app.tick();root.update()
        owner=OwnerConsole(app);owner.withdraw();root.update()
        assert not owner.auto and not owner.busy
        assert 'EXPERIMENTAL' in owner.experimental_notice.cget('text')
        with tempfile.TemporaryDirectory() as directory:
            owner.paths=(str(Path(directory)/'owner.db'),str(Path(directory)/'external.key'))
            owner.run('open',create=True)
            deadline=time.monotonic()+5
            while owner.busy and time.monotonic()<deadline:root.update();time.sleep(.01)
            assert not owner.busy
            assert 'Initialize' in owner.status.get()
            owner.run('list')
            deadline=time.monotonic()+5
            while owner.busy and time.monotonic()<deadline:root.update();time.sleep(.01)
            assert not owner.busy and not owner.members.get_children()
        owner.close()
    finally:app.close();root.destroy()
print('PASS: three path UI starts private, no network, no disclosure or sharing consent preselected')
