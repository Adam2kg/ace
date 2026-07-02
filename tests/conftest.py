"""Ensure tests import the ace package from THIS checkout, not an installed
copy or a sibling worktree that happens to be on sys.path first."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
