# SPDX-License-Identifier: Apache-2.0
"""Exercise actual Tk controls without playing audio or opening private data."""
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import tkinter as tk
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from flockoff_red_tape.desktop import App
from flockoff_red_tape.hounds import MESSAGE

sound = Mock(SND_FILENAME=1, SND_ASYNC=2, SND_NODEFAULT=4)
with patch.dict(sys.modules, {'winsound': sound}):
    root = tk.Tk(); root.withdraw(); app = App(root)
    try:
        root.update()
        sound.PlaySound.assert_not_called()
        assert app.hounds_message.get() == ''
        assert str(app.hounds_button.cget('takefocus')) == '1'
        app.hounds_button.invoke(); app.hounds_button.invoke(); root.update()
        assert app.hounds_message.get() == MESSAGE
        assert sound.PlaySound.call_count == 2
        assert app.case is None and app.desk is None
        sound.PlaySound.side_effect = RuntimeError('audio unavailable')
        app.hounds_button.invoke(); root.update()
        assert 'Audio unavailable' in app.hounds_message.get()
        sound.PlaySound.side_effect = None
    finally:
        app.close()
    sound.PlaySound.assert_called_with(None, 0)
print('PASS: silent startup, focusable native button, repeated click, text fallback, unchanged workspace, close cancellation')
