import subprocess
import sys
from pathlib import Path

from src.config import REPO_ROOT

def test_cli_runs_new_proposal():
    p = subprocess.run([sys.executable, "-m", "src.interface.cli", "--proposal", "episodic memory for agents"], cwd=REPO_ROOT, text=True, capture_output=True)
    assert p.returncode == 0
    assert "PROPOSAL GROUNDING" in p.stdout
    assert "POSITIONING" in p.stdout
