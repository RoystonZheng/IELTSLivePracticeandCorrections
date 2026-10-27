"""Compatibility entry point for the season-aware updater."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bank_update import update_once

if __name__ == '__main__':
    update_once()
