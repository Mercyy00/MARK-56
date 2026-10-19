"""
run_holo.py — J.A.R.V.I.S. MARK LVI 3D Holographic Neural Core Launcher
Launches Mark 56 with the React + Three.js 3D Holographic Neural Core as the native desktop UI.
"""

import sys
from pathlib import Path

# Ensure root directory is on PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import main

if __name__ == "__main__":
    main()
