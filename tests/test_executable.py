import os
import struct
import subprocess
import pytest

import sys

EXE_PATH = os.environ.get("HEADRUSH_EXE_PATH") or "c:/VM/HeadRush_NAM_Studio_Pro.exe"
if not os.path.exists(EXE_PATH):
    EXE_PATH = "c:/VM/HeadRush_NAM_Studio.exe"

def test_executable_pe_header_and_integrity():
    """Validates that the compiled binary is a valid 64-bit Windows PE executable."""
    if sys.platform != "win32" or not os.path.exists(EXE_PATH):
        pytest.skip(f"Executable test skipped (binary not found at {EXE_PATH} on this test runner)")
    
    file_size = os.path.getsize(EXE_PATH)
    assert file_size > 15 * 1024 * 1024, f"Executable unexpectedly small ({file_size} bytes), bundle likely corrupted"
    
    with open(EXE_PATH, "rb") as f:
        dos_header = f.read(64)
        assert dos_header[:2] == b"MZ", "Missing DOS 'MZ' magic number"
        
        # Read offset to PE header
        pe_offset = struct.unpack_from("<I", dos_header, 60)[0]
        f.seek(pe_offset)
        pe_sig = f.read(4)
        assert pe_sig == b"PE\x00\x00", "Missing PE signature"
        
        # Read COFF header
        coff_header = f.read(20)
        machine = struct.unpack_from("<H", coff_header, 0)[0]
        # 0x8664 is AMD64 / x86_64
        assert machine == 0x8664, f"Expected x86_64 machine architecture (0x8664), got {hex(machine)}"

def test_executable_smoke_launch(tmp_path):
    """
    Executes HeadRush_NAM_Studio.exe with working directory outside its folder,
    verifying it resolves internal modules without crashing or throwing ModuleNotFoundError.
    """
    if sys.platform != "win32" or not os.path.exists(EXE_PATH):
        pytest.skip(f"Executable not found at {EXE_PATH} on this platform")

    # Launch from isolated temp directory to test path independence
    proc = subprocess.Popen(
        [EXE_PATH],
        cwd=str(tmp_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        # If it crashes upon startup, wait(timeout=4) will return immediately
        exit_code = proc.wait(timeout=4.0)
        stdout, stderr = proc.communicate()
        assert exit_code == 0, f"Executable crashed with code {exit_code}!\nStderr: {stderr.decode(errors='ignore')}\nStdout: {stdout.decode(errors='ignore')}"
    except subprocess.TimeoutExpired:
        # Still running after 4 seconds confirms GUI entered its mainloop cleanly
        proc.kill()
        proc.wait()
