import os
import json
import pytest
import shutil
import sys

# Ensure src is in python search path
SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import headrush_manager as hm

REALISTIC_WAVENET_MODEL = {
    "version": "0.5.2",
    "architecture": "WaveNet",
    "config": {
        "layers": 10,
        "channels": 16,
        "head": "standard"
    },
    "sample_rate": 48000,
    "metadata": {
        "name": "Mesa Boogie Dual Rectifier Solo Head Ch3 Modern",
        "author": "NAM Audio Lab",
        "description": "High gain channel 3 modern mode with silicon diodes",
        "gear": "Mesa Boogie Dual Rectifier into Torpedo Captor X",
        "date": "2026-05-12",
        "esr": 0.00942
    },
    "weights": [0.123, -0.456, 0.789, 0.012, -0.345]
}

REALISTIC_LSTM_MODEL = {
    "version": "0.5.2",
    "architecture": "LSTM",
    "config": {
        "hidden_size": 24,
        "num_layers": 1
    },
    "sample_rate": 48000,
    "metadata": {
        "name": "Klon Centaur Gold Horsie Clean Boost",
        "author": "Vintage Tone Studio",
        "description": "Transparent overdrive at 9 o'clock gain",
        "gear": "Original 1994 Klon Centaur",
        "date": "2026-03-20",
        "esr": 0.00418
    },
    "weights": [0.05, -0.12, 0.33, 0.88]
}

@pytest.fixture
def realistic_nam_files(tmp_path):
    """Creates realistic .nam files on disk for testing."""
    models_dir = tmp_path / "sample_models"
    os.makedirs(models_dir, exist_ok=True)
    
    wavenet_path = models_dir / "Mesa_Dual_Rectifier.nam"
    wavenet_path.write_text(json.dumps(REALISTIC_WAVENET_MODEL, indent=2), encoding="utf-8")
    
    lstm_path = models_dir / "Klon_Centaur_Boost.nam"
    lstm_path.write_text(json.dumps(REALISTIC_LSTM_MODEL, indent=2), encoding="utf-8")
    
    corrupt_path = models_dir / "Corrupt_Truncated.nam"
    corrupt_path.write_text('{"version": "0.5.2", "metadata": {"name": "Broken', encoding="utf-8")
    
    binary_junk_path = models_dir / "Binary_Garbage.nam"
    binary_junk_path.write_bytes(b"\x00\xff\xfe\xca\xfe\xba\xbe" * 50)
    
    return {
        "dir": str(models_dir),
        "wavenet": str(wavenet_path),
        "lstm": str(lstm_path),
        "corrupt": str(corrupt_path),
        "binary": str(binary_junk_path)
    }

@pytest.fixture
def mock_pedal_drive(tmp_path):
    """Creates a mock HeadRush pedalboard USB directory tree."""
    orig_drive = hm.get_drive()
    drive_path = tmp_path / "HeadRush_USB_Drive"
    
    os.makedirs(drive_path / "NAM", exist_ok=True)
    os.makedirs(drive_path / "Blocks" / "ANXIETY OD", exist_ok=True)
    os.makedirs(drive_path / "Blocks" / "ANXIETY OD V2", exist_ok=True)
    os.makedirs(drive_path / "Blocks" / "IR", exist_ok=True)
    os.makedirs(drive_path / "Impulse Responses", exist_ok=True)
    os.makedirs(drive_path / "Rigs", exist_ok=True)
    
    drive_str = str(drive_path)
    hm.set_drive(drive_str)
    
    yield drive_str
    
    hm.set_drive(orig_drive)

@pytest.fixture
def populated_pedal_drive(mock_pedal_drive, realistic_nam_files):
    """
    Sets up a realistic pedalboard with multiple active slots, custom trims,
    IRs, and specific naming conventions.
    """
    # Slot 0: Mesa Dual Rectifier (Tone=45, Level=65)
    hm.install_nam_to_headrush(
        realistic_nam_files["wavenet"],
        custom_name="MESA RECTO LEAD",
        slot=0,
        tone=45,
        level=65
    )
    
    # Slot 12: Klon Boost (Tone=60, Level=80)
    hm.install_nam_to_headrush(
        realistic_nam_files["lstm"],
        custom_name="KLON CLEAN BOOST",
        slot=12,
        tone=60,
        level=80
    )
    
    # Slot 47: Friedman BE100
    f_path = os.path.join(realistic_nam_files["dir"], "Friedman_BE100.nam")
    with open(f_path, 'w', encoding='utf-8') as f:
        json.dump({"version": "0.5.2", "architecture": "WaveNet", "metadata": {"name": "Friedman BE100 Brown Eye"}}, f)
    hm.install_nam_to_headrush(f_path, custom_name="FRIEDMAN BE100", slot=47, tone=52, level=72)
    
    # Slot 99: Soldano SLO100 (near maximum limit)
    s_path = os.path.join(realistic_nam_files["dir"], "Soldano_SLO100.nam")
    with open(s_path, 'w', encoding='utf-8') as f:
        json.dump({"version": "0.5.2", "architecture": "WaveNet", "metadata": {"name": "Soldano SLO100 Lead Crunch"}}, f)
    hm.install_nam_to_headrush(s_path, custom_name="SOLDANO SLO LEAD", slot=99, tone=48, level=68)
    
    return mock_pedal_drive
