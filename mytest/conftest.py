"""Pytest fixtures for the GBQA computer-use refactor."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT_DIR / "agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))


@pytest.fixture()
def temp_dir(tmp_path):
    return tmp_path
