"""Run the source checkout without an editable install."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from flockoff_red_tape.desktop import main

main()
