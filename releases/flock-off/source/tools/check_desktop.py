"""Native Tk widget integration checks; no external services or real case data."""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import tkinter as tk
from flockoff_red_tape.desktop import App, Form


def run():
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        root = tk.Tk(); root.withdraw()
        app = App(root)
        try:
            app.use(directory / 'desk.sqlite', directory / 'key', True)
            example = json.loads((Path(__file__).resolve().parents[1] / 'docs/red_tape/examples/case.json').read_text())
            app.desk.save(example, 0)
            app.refresh(example['id']); root.update()
            assert app.receipt['revision'] == 1
            assert len(app.tables['assessment'].get_children()) == 12
            assert 'Metadata only' in app.tables['sources'].item('E01')['values']
            app.edit_record('sources', True); root.update()
            form = next(w for w in root.winfo_children() if isinstance(w, Form))
            # A failed save must retain the form, and retry must not append twice.
            with patch('flockoff_red_tape.desktop.messagebox.showerror') as error:
                form.save()
                assert error.called
            for key, kind, getter in form.widgets:
                if key == 'id': continue
                widget = getattr(getter, '__self__', None)
                if widget is not None and key in example['sources'][0]:
                    if kind == 'content_kind': widget.set('paraphrase')
                    else:
                        widget.delete(0, 'end'); widget.insert(0, example['sources'][0][key])
            # Text widgets have closure getters; fill the two paragraph fields directly.
            for key, kind, getter in form.widgets:
                if kind == 'paragraph':
                    widget = getter.__defaults__[0]
                    widget.delete('1.0', 'end'); widget.insert('1.0', example['sources'][0][key])
            form.save(); root.update()
            assert len(app.case['sources']) == 2
            assert app.receipt['revision'] == 2
            app.tables['sources'].selection_set('E01'); app.view_record('sources'); root.update()
            app.review(); root.update()
            review = next(w for w in root.winfo_children() if isinstance(w, Form))
            assert all(not getter() for _, kind, getter in review.widgets if kind == 'boolean')
            review.destroy()
            app.select_questions(); root.update()
            selection = next(w for w in root.winfo_children() if isinstance(w, Form))
            selection.save(); root.update()
            assert app.case['selected_questions'] == ['Q01']
            app.desk.close(); app.desk = None
            app.use(directory / 'desk.sqlite', directory / 'key')
            app.refresh(example['id']); root.update()
            assert len(app.case['sources']) == 2
            print('PASS: native widgets, failed-save retry, unselected review checks, case selection, persistence and reopen')
        finally:
            app.close()


if __name__ == '__main__': run()
