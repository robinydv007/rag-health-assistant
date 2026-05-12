"""Add service src to path so tests can import from src.*"""
import sys
from pathlib import Path

# Makes `from src.main import app` work
sys.path.insert(0, str(Path(__file__).parent.parent))
