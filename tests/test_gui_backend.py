import os
import json
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from app_gui import HeadRushBackend

def test_headrush_backend_initialization(tmp_path):
    backend = HeadRushBackend(drive=str(tmp_path))
    assert backend.drive == str(tmp_path)
    assert backend.nam_dir == os.path.join(str(tmp_path), "NAM")
    assert backend.blocks_v1_dir == os.path.join(str(tmp_path), "Blocks", "ANXIETY OD")
    assert backend.blocks_v2_dir == os.path.join(str(tmp_path), "Blocks", "ANXIETY OD V2")
    assert backend.ir_dir == os.path.join(str(tmp_path), "Impulse Responses")
    assert backend.ir_blocks_dir == os.path.join(str(tmp_path), "Blocks", "IR")

def test_backend_connection_detection(tmp_path):
    backend = HeadRushBackend(drive=str(tmp_path))
    # Not connected initially
    assert backend.is_connected() is False
    
    # Create Rigs directory
    os.makedirs(os.path.join(str(tmp_path), "Rigs"), exist_ok=True)
    assert backend.is_connected() is True

def test_backend_model_installation_and_trims(tmp_path):
    mock_drive = str(tmp_path)
    backend = HeadRushBackend(drive=mock_drive)
    os.makedirs(os.path.join(mock_drive, "NAM"), exist_ok=True)
    
    # Create dummy source NAM file
    src_file = tmp_path / "test_amp.nam"
    src_file.write_text("TEST_MODEL", encoding='utf-8')
    
    # Install
    res = backend.install_model(str(src_file), preset_name="JP2C LEAD", slot=5, tone=60, level=75)
    assert res["slot"] == 5
    assert res["preset_name"] == "JP2C LEAD"
    
    slots = backend.get_installed_slots()
    assert 5 in slots
    assert slots[5]["slot"] == 5
    
    # Update trims
    success = backend.update_slot_trims(5, preset_name="JP2C LEAD WARM", tone=40, level=85)
    assert success is True
    
    # Delete
    del_ok = backend.delete_slot(5)
    assert del_ok is True
    assert 5 not in backend.get_installed_slots()

def test_backend_ir_block_creation(tmp_path):
    mock_drive = str(tmp_path)
    backend = HeadRushBackend(drive=mock_drive)
    
    ir_path = backend.create_ir_block(
        preset_name="MESA 4x12 V30",
        ir_folder="Mesa OS 4x12",
        ir_name="Mesa_OS_V30_Cap_57",
        gain=-6.0
    )
    assert os.path.exists(ir_path)
    with open(ir_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        assert data["type"] == "IR"

def test_backend_pro_methods(tmp_path):
    mock_drive = str(tmp_path / "hr_usb")
    backend = HeadRushBackend(drive=mock_drive)
    os.makedirs(os.path.join(mock_drive, "NAM"), exist_ok=True)
    os.makedirs(os.path.join(mock_drive, "Blocks", "ANXIETY OD"), exist_ok=True)
    os.makedirs(os.path.join(mock_drive, "Blocks", "ANXIETY OD V2"), exist_ok=True)
    
    # Test smart formatting
    formatted = backend.smart_format_preset_name("Mesa_Boogie_Mark_V_Lead")
    assert "MESA" in formatted
    
    # Test batch import
    src_dir = tmp_path / "models"
    os.makedirs(src_dir, exist_ok=True)
    (src_dir / "Amp1.nam").write_text("{\"model\": 1}", encoding='utf-8')
    (src_dir / "Amp2.nam").write_text("{\"model\": 2}", encoding='utf-8')
    
    res = backend.import_local_models_batch([str(src_dir)])
    assert res["count"] == 2
    
    # Storage status
    st = backend.get_storage_status()
    assert st["slots_used"] == 2
    
    # Health check
    hc = backend.perform_health_check()
    assert hc["healthy"] is True
    
    # Safe eject
    ej = backend.safe_eject()
    assert ej["safe_to_disconnect"] is True
    
    # Cheat sheet
    cs = backend.generate_stage_cheat_sheet("txt")
    assert "Amp1" in cs or "Amp2" in cs
    
    # Duplicates
    dups = backend.detect_duplicate_models()
    assert "total_duplicates" in dups

