"""Pytest configuration - add parent directory to Python path for module resolution."""
import sys
from pathlib import Path

# Add parent directory and scripts directory to sys.path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "scripts"))
