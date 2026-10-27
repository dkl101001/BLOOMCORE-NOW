# SPDX-License-Identifier: Apache-2.0
import sys
from pathlib import Path
import tkinter as tk
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from flockoff_red_tape.research_ui import ResearchWindow
root=tk.Tk();root.withdraw()
with patch('flockoff_research.agent.PublicTransport.fetch',side_effect=AssertionError('unexpected network')):
    window=ResearchWindow(root);window.withdraw()
    try:
        root.update();window.tick();root.update()
        assert not window.enabled and window.worker is None
        assert 'EXPERIMENTAL' in window.experimental_notice.cget('text')
        assert 'privacy is unvalidated' in window.experimental_notice.cget('text')
        assert not window.consent.get() and not window.rules.get()
        assert window.urls.get('1.0','end-1c')==''
        window.records=[{'source_url':'https://example.org/public','source_text':'<script>synthetic text only</script>','claim_state':'unknown','encountered_at':'fixture'}]
        window.history.insert('', 'end',iid='0');window.history.selection_set('0');window.show()
        assert '<script>synthetic text only</script>' in window.content.get('1.0','end')
        assert window.content.cget('state')=='disabled'
    finally:window.close();root.destroy()
print('PASS: research UI starts disabled, no network; untrusted source text displayed literally')
