"""Pytest configuration file to set up the Python path for testing."""

import sys
from pathlib import Path

# Add the app directory to Python path so that 'src' imports work
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))
