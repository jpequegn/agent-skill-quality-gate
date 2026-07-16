from __future__ import annotations

import subprocess
import sys


def test_module_help_describes_the_local_cli() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "agent_skill_quality_gate", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Local-first linting" in result.stdout
    assert "--version" in result.stdout
