# SPDX-License-Identifier: Apache-2.0
"""Opt-in, local synthetic bark. Never called at startup; no background worker."""
from pathlib import Path

MESSAGE = 'THE HOUNDS HAVE ACKNOWLEDGED YOUR PRESENCE.'


class Hounds:
    def __init__(self):
        self.closed = False
        self.playing = False

    def release(self):
        if self.closed:
            return ''
        try:
            import winsound
            winsound.PlaySound(str(Path(__file__).with_name('resources') / 'bark.wav'),
                               winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            self.playing = True
            return MESSAGE
        except (ImportError, OSError, RuntimeError):
            return MESSAGE + ' (Audio unavailable.)'

    def close(self):
        self.closed = True
        if self.playing:
            try:
                import winsound
                winsound.PlaySound(None, 0)
            except (ImportError, OSError, RuntimeError):
                pass
            self.playing = False
