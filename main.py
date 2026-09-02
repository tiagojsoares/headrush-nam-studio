#!/usr/bin/env python3
"""
HeadRush NAM Studio Pro - Main Entry Point
Run the GUI or CLI interface directly from the repository root.
"""
import sys
import os

# Add src/ to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        from headrush_cli import main as cli_main
        sys.argv.pop(1)
        cli_main()
    else:
        from app_gui import main as gui_main
        gui_main()
