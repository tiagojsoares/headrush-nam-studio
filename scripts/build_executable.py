#!/usr/bin/env python3
"""
Python build script to generate the HeadRush NAM Studio standalone executable.
"""
import sys
import subprocess
import os

def build():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_script = os.path.join(root_dir, "main.py")
    src_dir = os.path.join(root_dir, "src")
    dist_dir = os.path.join(root_dir, "dist")
    
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "HeadRush_NAM_Studio",
        "--paths", src_dir,
        "--hidden-import", "app_gui",
        "--hidden-import", "headrush_manager",
        "--hidden-import", "headrush_cli",
        "--collect-all", "customtkinter",
        "--distpath", dist_dir,
        main_script,
        "--clean",
        "-y"
    ]
    
    print(f"Building HeadRush NAM Studio from {main_script}...")
    print(f"Command: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=root_dir)
    print(f"\n[OK] Build completed successfully. Binary is at: {os.path.join(dist_dir, 'HeadRush_NAM_Studio.exe')}")

if __name__ == "__main__":
    build()
