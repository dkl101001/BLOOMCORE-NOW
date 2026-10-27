# SPDX-License-Identifier: Apache-2.0
import sys
import unittest
from unittest.mock import Mock, patch
from flockoff_red_tape.hounds import Hounds, MESSAGE


class HoundsTests(unittest.TestCase):
    def test_silent_startup(self):
        with patch.dict(sys.modules, {'winsound': Mock()}) as modules:
            Hounds()
            modules['winsound'].PlaySound.assert_not_called()

    def test_click_and_repeat_are_async_and_bounded(self):
        sound = Mock(SND_FILENAME=1, SND_ASYNC=2, SND_NODEFAULT=4)
        with patch.dict(sys.modules, {'winsound': sound}):
            h = Hounds()
            self.assertEqual(h.release(), MESSAGE)
            self.assertEqual(h.release(), MESSAGE)
            self.assertEqual(sound.PlaySound.call_count, 2)
            path, flags = sound.PlaySound.call_args.args
            from pathlib import Path
            self.assertTrue(Path(path).is_file())
            self.assertEqual(flags, 7)

    def test_audio_failure_text_fallback(self):
        sound = Mock(SND_FILENAME=1, SND_ASYNC=2, SND_NODEFAULT=4)
        sound.PlaySound.side_effect = RuntimeError('unavailable')
        with patch.dict(sys.modules, {'winsound': sound}):
            self.assertIn(MESSAGE, Hounds().release())
            self.assertIn('Audio unavailable', Hounds().release())

    def test_close_stops_audio_and_prevents_replay(self):
        sound = Mock(SND_FILENAME=1, SND_ASYNC=2, SND_NODEFAULT=4)
        with patch.dict(sys.modules, {'winsound': sound}):
            h = Hounds(); h.release(); h.close()
            sound.PlaySound.assert_called_with(None, 0)
            self.assertEqual(h.release(), '')
            self.assertEqual(sound.PlaySound.call_count, 2)

    def test_unsupported_platform_is_text_only(self):
        with patch.dict(sys.modules, {'winsound': None}):
            self.assertIn('Audio unavailable', Hounds().release())
