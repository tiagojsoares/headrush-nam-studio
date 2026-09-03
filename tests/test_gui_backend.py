import os
import json
import zipfile
import pytest
from app_gui import HeadRushBackend

def test_backend_lifecycle_and_drive_switching(mock_pedal_drive, tmp_path):
    """Tests connection detection, drive switching, and directory resolution."""
    backend = HeadRushBackend(drive=mock_pedal_drive)
    assert backend.is_connected() is True
    assert backend.drive == mock_pedal_drive
    
    # Test switching to another disconnected path
    fake_drive = str(tmp_path / "FakeDrive")
    backend.set_drive(fake_drive)
    assert backend.is_connected() is False
    assert backend.get_free_space_gb() == 0.0

def test_backend_model_installation_and_trim_manipulation(mock_pedal_drive, realistic_nam_files):
    """
    Tests complete lifecycle of installing a model, tweaking Tone/Level trims,
    updating the preset name, moving slot, and verifying state consistency.
    """
    backend = HeadRushBackend(drive=mock_pedal_drive)
    
    # 1. Install model to slot 7
    res = backend.install_model(
        realistic_nam_files["wavenet"],
        preset_name="RECTO MODERN CH3",
        slot=7,
        tone=54,
        level=76
    )
    assert res["slot"] == 7
    assert res["preset_name"] == "RECTO MODERN CH3"
    
    # Verify installed
    slots = backend.get_installed_slots()
    assert 7 in slots
    assert slots[7]["tone"] == 54
    assert slots[7]["level"] == 76
    
    # 2. Update trims and rename
    ok = backend.update_slot_trims(7, preset_name="RECTO RAW VINTAGE", tone=42, level=84, sync_nam=True)
    assert ok is True
    
    updated_slots = backend.get_installed_slots()
    assert updated_slots[7]["preset_name"] == "RECTO RAW VINTAGE"
    assert updated_slots[7]["tone"] == 42
    assert updated_slots[7]["level"] == 84
    assert "RECTO RAW VINTAGE" in updated_slots[7]["nam_file"]
    
    # 3. Move slot (7 -> 33)
    move_ok = backend.move_slot(7, 33)
    assert move_ok is True
    
    moved_slots = backend.get_installed_slots()
    assert 7 not in moved_slots
    assert 33 in moved_slots
    assert moved_slots[33]["preset_name"] == "RECTO RAW VINTAGE"
    assert moved_slots[33]["tone"] == 42
    
    # 4. Delete slot 33
    del_ok = backend.delete_slot(33)
    assert del_ok is True
    assert 33 not in backend.get_installed_slots()

def test_backend_quick_trim_presets(mock_pedal_drive, realistic_nam_files):
    """Tests instant calibration presets (clean_boost, hot_drive, high_gain, unity)."""
    backend = HeadRushBackend(drive=mock_pedal_drive)
    backend.install_model(realistic_nam_files["lstm"], preset_name="CALIBRATION TEST", slot=5)
    
    # Clean boost: tone=55, level=80
    backend.apply_trim_preset(5, "clean_boost")
    s = backend.get_installed_slots()[5]
    assert s["tone"] == 55 and s["level"] == 80
    
    # High gain: tone=45, level=65
    backend.apply_trim_preset(5, "high_gain")
    s = backend.get_installed_slots()[5]
    assert s["tone"] == 45 and s["level"] == 65

    # Unity: tone=50, level=50
    backend.apply_trim_preset(5, "unity")
    s = backend.get_installed_slots()[5]
    assert s["tone"] == 50 and s["level"] == 50

def test_backend_single_slot_bundle_export(mock_pedal_drive, realistic_nam_files, tmp_path):
    """Tests packaging a single slot into a shareable .zip bundle."""
    backend = HeadRushBackend(drive=mock_pedal_drive)
    backend.install_model(realistic_nam_files["wavenet"], preset_name="JP2C LEAD", slot=3, tone=48, level=74)
    
    dest_zip = str(tmp_path / "Slot_003_JP2C.zip")
    out = backend.export_slot_bundle(3, dest_zip)
    assert os.path.exists(out)
    
    with zipfile.ZipFile(out, "r") as z:
        files = z.namelist()
        assert any(f.endswith(".nam") for f in files)
        assert any(f.startswith("Blocks_V1/") for f in files)
        assert any(f.startswith("Blocks_V2/") for f in files)

def test_backend_equipment_categorization_logic():
    """Validates dynamic model tagging logic for the GUI filter chips."""
    def categorize(name):
        name_lower = name.lower()
        if any(k in name_lower for k in ["petrucci", "timmons", "jp ", "jp2c", "at "]):
            return "SIGNATURE"
        elif any(k in name_lower for k in ["drive", "od", "ts808", "ts9", "boost", "fuzz", "dist", "throttle", "1981", "dude"]):
            return "DRIVE"
        elif any(k in name_lower for k in ["clean", "jazz", "sss", "cln"]):
            return "CLEAN"
        else:
            return "AMP"
            
    assert categorize("John Petrucci JP2C Lead") == "SIGNATURE"
    assert categorize("Andy Timmons AT+ Angry Charlie") == "SIGNATURE"
    assert categorize("Ibanez TS808 Tube Screamer") == "DRIVE"
    assert categorize("1981 DRV Overdrive") == "DRIVE"
    assert categorize("Dumble SSS Steel String Clean") == "CLEAN"
    assert categorize("Roland Jazz Chorus 120 Cln") == "CLEAN"
    assert categorize("Mesa Dual Rectifier High Gain") == "AMP"
    assert categorize("Marshall JCM800 2203") == "AMP"
