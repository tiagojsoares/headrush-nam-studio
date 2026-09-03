import os
import subprocess
import pytest

def test_executable_smoke_launch():
    exe_path = "c:/VM/HeadRush_NAM_Studio.exe"
    if not os.path.exists(exe_path):
        pytest.skip("Executable not found at c:/VM/HeadRush_NAM_Studio.exe")

    # Launch the executable with a short timeout.
    # If there is a ModuleNotFoundError or unhandled exception, it exits immediately with non-zero or pops up crash.
    # If it launches successfully, it stays running until killed.
    try:
        proc = subprocess.Popen(
            [exe_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        try:
            exit_code = proc.wait(timeout=3.5)
            stdout, stderr = proc.communicate()
            assert exit_code == 0, f"Executable crashed immediately with code {exit_code}.\nStderr: {stderr.decode(errors='ignore')}\nStdout: {stdout.decode(errors='ignore')}"
        except subprocess.TimeoutExpired:
            # Still running after 3.5s means the GUI started cleanly without crashing!
            proc.kill()
            proc.wait()
    except Exception as e:
        pytest.fail(f"Failed to launch executable: {e}")
