#!/usr/bin/env python3
"""
Main entry point for Local AI Assistant.

This script ensures Python can properly import the local_ai_assistant package
by adjusting the Python path if needed.
"""

import os
import sys
from pathlib import Path


def main():
    """Set up Python path and run the assistant."""
    # Get the directory containing this script
    script_dir = Path(__file__).resolve().parent
    
    # Add the parent directory to Python path if needed
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    
    # Now import and run the actual main module
    from local_ai_assistant.main import main as run_assistant
    return run_assistant()


if __name__ == "__main__":
    sys.exit(main()) 