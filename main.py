#!/usr/bin/env python3
"""
HeadRush NAM Studio Pro - Main Entry Point
Run the GUI or CLI interface directly from the repository root.
"""
import sys
import os

# Ensure src directory is in sys.path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import headrush_manager
import app_gui
import headrush_cli

def run():
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        sys.argv.pop(1)
        headrush_cli.main()
    else:
        app_gui.main()

if __name__ == "__main__":
    run()
