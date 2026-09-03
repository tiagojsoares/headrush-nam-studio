import os
import json
import pytest
import sys

# Ensure src is in python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

import headrush_manager as hm

def test_sanitize_for_headrush():
    assert hm.sanitize_for_headrush("Mesa/Boogie: Dual Rectifier! (Modern)") == "MesaBoogie Dual Rectifier"
    # Test length clipping
    long_name = "A" * 50
    assert len(hm.sanitize_for_headrush(long_name, max_len=26)) == 26

def test_drive_and_path_getters(tmp_path):
    orig_drive = hm.get_drive()
    try:
        custom_drive = str(tmp_path)
        hm.set_drive(custom_drive)
        assert hm.get_drive().rstrip("/\\") == custom_drive.rstrip("/\\")
        assert hm.get_nam_dir() == os.path.join(custom_drive, "NAM")
        assert hm.get_blocks_v1_dir() == os.path.join(custom_drive, "Blocks", "ANXIETY OD")
        assert hm.get_blocks_v2_dir() == os.path.join(custom_drive, "Blocks", "ANXIETY OD V2")
        assert hm.get_ir_dir() == os.path.join(custom_drive, "Impulse Responses")
        assert hm.get_ir_blocks_dir() == os.path.join(custom_drive, "Blocks", "IR")
    finally:
        hm.set_drive(orig_drive)

def test_create_block_preset_dual_compatibility(tmp_path):
    orig_drive = hm.get_drive()
    try:
        hm.set_drive(str(tmp_path))
        created_paths = hm.create_block_preset(slot_num=28, preset_name="1981 DRV", tone=45, level=75)
        
        assert len(created_paths) == 2
        
        # Verify V1 block
        v1_path = created_paths[0]
        assert os.path.exists(v1_path)
        with open(v1_path, 'r', encoding='utf-8') as f:
            v1_data = json.load(f)
            assert v1_data["type"] == "ANXIETY OD"
            assert v1_data["readonly"] is False
            inner = json.loads(v1_data["content"])
            pedal = inner["data"]["Anxiety OD"]["children"]
            assert pedal["Drive"]["value"] == 28
            assert pedal["Tone"]["value"] == 45
            assert pedal["Level"]["value"] == 75
            
        # Verify V2 block
        v2_path = created_paths[1]
        assert os.path.exists(v2_path)
        with open(v2_path, 'r', encoding='utf-8') as f:
            v2_data = json.load(f)
            assert v2_data["type"] == "ANXIETY OD V2"
            assert v2_data["readonly"] is False
            inner = json.loads(v2_data["content"])
            pedal = inner["data"]["Anxiety OD V2"]["children"]
            assert pedal["Drive"]["value"] == 28
            assert pedal["Tone"]["value"] == 45
            assert pedal["Level"]["value"] == 75
    finally:
        hm.set_drive(orig_drive)

def test_create_ir_block_preset(tmp_path):
    orig_drive = hm.get_drive()
    try:
        hm.set_drive(str(tmp_path))
        ir_block_path = hm.create_ir_block_preset(
            preset_name="EVH 5150 CAB",
            ir_folder="Celestion EVH 5150",
            ir_name="EVH_4x12_SM57_Center",
            gain=-8.5,
            hi_cut=9500,
            lo_cut=60
        )
        assert os.path.exists(ir_block_path)
        with open(ir_block_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data["type"] == "IR"
            inner = json.loads(data["content"])
            ir_obj = inner["data"]["IR"]["children"]
            assert ir_obj["Gain"]["value"] == -8.5
            assert ir_obj["HiCut"]["value"] == 9500
            assert ir_obj["LoCut"]["value"] == 60
            assert ir_obj["IR"]["string"] == "[directory](Celestion EVH 5150)[name](EVH_4x12_SM57_Center)"
    finally:
        hm.set_drive(orig_drive)

def test_slot_management_and_installation(tmp_path):
    orig_drive = hm.get_drive()
    try:
        mock_drive = str(tmp_path)
        hm.set_drive(mock_drive)
        
        # Create minimal required folders for connection detection
        os.makedirs(os.path.join(mock_drive, "Blocks"), exist_ok=True)
        assert hm.is_headrush_connected() is True
        
        # Initial state should have slot 0 available
        assert hm.get_next_free_slot() == 0
        
        # Create a dummy source .nam file
        src_nam = tmp_path / "dummy_tone.nam"
        src_nam.write_text("DUMMY_NAM_DATA", encoding='utf-8')
        
        # Install model
        res = hm.install_nam_to_headrush(str(src_nam), custom_name="DUMBLE ODS", slot=0, tone=55, level=80)
        assert res["slot"] == 0
        assert res["preset_name"] == "DUMBLE ODS"
        assert os.path.exists(res["nam_path"])
        
        # Now slot 0 is occupied, next free should be 1
        slots = hm.get_installed_slots()
        assert 0 in slots
        assert slots[0]["nam_name"] == "DUMBLE ODS"
        assert hm.get_next_free_slot() == 1
        
        # Test update_slot_trims
        hm.update_slot_trims(0, "DUMBLE CLEAN", tone=40, level=85, sync_nam_name=True)
        slots = hm.get_installed_slots()
        assert slots[0]["preset_name"] == "DUMBLE CLEAN"
        assert slots[0]["tone"] == 40
        assert slots[0]["level"] == 85
        assert "DUMBLE CLEAN" in slots[0]["nam_file"]
        
        # Test move_slot (0 -> 10)
        hm.move_slot(0, 10)
        slots = hm.get_installed_slots()
        assert 0 not in slots
        assert 10 in slots
        assert slots[10]["preset_name"] == "DUMBLE CLEAN"
        assert slots[10]["tone"] == 40
        
        # Delete slot 10
        del_success = hm.delete_slot(10)
        assert del_success is True
        assert 10 not in hm.get_installed_slots()
    finally:
        hm.set_drive(orig_drive)

def test_backup_and_restore(tmp_path):
    orig_drive = hm.get_drive()
    try:
        mock_drive = tmp_path / "headrush_drive"
        os.makedirs(mock_drive / "Blocks", exist_ok=True)
        hm.set_drive(str(mock_drive))
        
        # Install a model
        src_nam = tmp_path / "src.nam"
        src_nam.write_text("TEST", encoding='utf-8')
        hm.install_nam_to_headrush(str(src_nam), custom_name="PRE_BACKUP", slot=1)
        
        # Create backup
        backup_storage = tmp_path / "backups"
        bdir = hm.create_backup(target_root=str(backup_storage))
        assert os.path.exists(bdir)
        
        backups = hm.list_backups(target_root=str(backup_storage))
        assert len(backups) == 1
        
        # Modify slot 1
        hm.delete_slot(1)
        assert 1 not in hm.get_installed_slots()
        
        # Restore backup
        hm.restore_backup(bdir)
        slots = hm.get_installed_slots()
        assert 1 in slots
        assert slots[1]["preset_name"] == "PRE_BACKUP"
    finally:
        hm.set_drive(orig_drive)

def test_clean_orphaned_blocks_and_defrag(tmp_path):
    orig_drive = hm.get_drive()
    try:
        mock_drive = tmp_path / "headrush_drive"
        os.makedirs(mock_drive / "NAM", exist_ok=True)
        os.makedirs(mock_drive / "Blocks" / "ANXIETY OD", exist_ok=True)
        os.makedirs(mock_drive / "Blocks" / "ANXIETY OD V2", exist_ok=True)
        hm.set_drive(str(mock_drive))
        
        # Create models at slot 5 and slot 15
        src_a = tmp_path / "a.nam"
        src_a.write_text("A", encoding='utf-8')
        src_b = tmp_path / "b.nam"
        src_b.write_text("B", encoding='utf-8')
        
        hm.install_nam_to_headrush(str(src_a), custom_name="Zebra Amp", slot=5)
        hm.install_nam_to_headrush(str(src_b), custom_name="Alpha Amp", slot=15)
        
        # Create an orphaned block for slot 99 (no matching .nam file)
        hm.create_block_preset(99, "Orphaned Tone")
        assert any("099" in f for f in os.listdir(hm.get_blocks_v2_dir()))
        
        # Test clean_orphaned_blocks
        deleted = hm.clean_orphaned_blocks()
        assert len(deleted) > 0
        assert not any("099" in f for f in os.listdir(hm.get_blocks_v2_dir()))
        
        # Test defrag_and_reorder_slots (alphabetical)
        res = hm.defrag_and_reorder_slots(sort_by="alpha", make_safety_backup=False)
        assert res["count"] == 2
        
        slots = hm.get_installed_slots()
        assert 0 in slots
        assert 1 in slots
        assert 5 not in slots
        assert 15 not in slots
        # Alpha Amp should be slot 000, Zebra Amp slot 001
        assert slots[0]["preset_name"] == "Alpha Amp"
        assert slots[1]["preset_name"] == "Zebra Amp"
    finally:
        hm.set_drive(orig_drive)

def test_smart_format_preset_name():
    assert hm.smart_format_preset_name("Mesa_Boogie_Dual_Rectifier_Solo_Head_Ch3") == "MESA RECTO DUAL Solo Head"[:24].strip()
    assert "MESA" in hm.smart_format_preset_name("Mesa Boogie Mark V")
    assert "MRSHL" in hm.smart_format_preset_name("Marshall JCM800 Lead")
    assert "TS9" in hm.smart_format_preset_name("Ibanez Tube Screamer Overdrive")
    assert "DMBL" in hm.smart_format_preset_name("Dumble ODS Clean")
    assert len(hm.smart_format_preset_name("A" * 50)) <= 24

def test_inspect_nam_file(tmp_path):
    # Non-existent file
    res = hm.inspect_nam_file(str(tmp_path / "fake.nam"))
    assert res["valid"] is False

    # Valid NAM JSON
    valid_nam = tmp_path / "test_model.nam"
    sample_data = {
        "version": "0.5.1",
        "architecture": "Standard (WaveNet)",
        "sample_rate": 48000,
        "metadata": {
            "name": "Custom 5150",
            "author": "NAM Studio",
            "description": "High gain 5150 head",
            "esr": 0.012
        }
    }
    valid_nam.write_text(json.dumps(sample_data), encoding='utf-8')
    res = hm.inspect_nam_file(str(valid_nam))
    assert res["valid"] is True
    assert res["name"] == "Custom 5150"
    assert res["architecture"] == "Standard (WaveNet)"
    assert res["author"] == "NAM Studio"
    assert res["training_loss"] == 0.012

def test_batch_import_and_duplicates(tmp_path):
    orig_drive = hm.get_drive()
    try:
        mock_drive = tmp_path / "hr_drive"
        os.makedirs(mock_drive / "NAM", exist_ok=True)
        os.makedirs(mock_drive / "Blocks" / "ANXIETY OD", exist_ok=True)
        os.makedirs(mock_drive / "Blocks" / "ANXIETY OD V2", exist_ok=True)
        hm.set_drive(str(mock_drive))

        # Create 3 source files
        src_dir = tmp_path / "src_batch"
        os.makedirs(src_dir, exist_ok=True)
        (src_dir / "01_Friedman_BE100.nam").write_text("{\"model\": 1}", encoding='utf-8')
        (src_dir / "02_Soldano_SLO100.nam").write_text("{\"model\": 2}", encoding='utf-8')
        # Duplicate of Friedman
        (src_dir / "03_Friedman_Duplicate.nam").write_text("{\"model\": 1}", encoding='utf-8')

        batch_res = hm.import_local_models_batch([str(src_dir)], smart_rename=True)
        assert batch_res["count"] == 3
        
        # Check duplicate detector
        dupes = hm.detect_duplicate_models()
        assert dupes["total_duplicates"] >= 1
        assert len(dupes["hash_duplicates"]) == 1
    finally:
        hm.set_drive(orig_drive)

def test_setlists_and_cheat_sheet(tmp_path):
    orig_drive = hm.get_drive()
    try:
        mock_drive = tmp_path / "hr_drive"
        os.makedirs(mock_drive / "NAM", exist_ok=True)
        os.makedirs(mock_drive / "Blocks" / "ANXIETY OD", exist_ok=True)
        os.makedirs(mock_drive / "Blocks" / "ANXIETY OD V2", exist_ok=True)
        hm.set_drive(str(mock_drive))

        # Install a model
        f = tmp_path / "amp.nam"
        f.write_text("{}", encoding='utf-8')
        hm.install_nam_to_headrush(str(f), custom_name="Stage Lead", slot=0, tone=55, level=75)

        # Save Setlist
        s_dir = hm.save_setlist("Rock_Gig", root=str(tmp_path / "setlists"))
        assert os.path.exists(s_dir)
        
        lists = hm.list_setlists(root=str(tmp_path / "setlists"))
        assert len(lists) == 1
        assert lists[0]["name"] == "Rock_Gig"

        # Export and Import Setlist Zip
        zip_p = str(tmp_path / "export_setlist.zip")
        hm.export_setlist_zip("Rock_Gig", zip_p, root=str(tmp_path / "setlists"))
        assert os.path.exists(zip_p)

        # Cheat sheet test
        txt_sheet = hm.generate_stage_cheat_sheet(output_format="txt")
        assert "Stage Lead" in txt_sheet
        assert "000" in txt_sheet

        md_sheet = hm.generate_stage_cheat_sheet(output_format="md")
        assert "| `000` |" in md_sheet

        html_sheet = hm.generate_stage_cheat_sheet(output_format="html")
        assert "Stage Lead" in html_sheet
        assert "<table" in html_sheet

        # Storage status
        status = hm.get_storage_status()
        assert status["slots_used"] == 1

        # Health check
        health = hm.perform_health_check()
        assert health["score"] >= 80

        # Export slot bundle
        bundle_p = str(tmp_path / "slot0_bundle.zip")
        hm.export_slot_bundle(0, bundle_p)
        assert os.path.exists(bundle_p)

        # Apply trim preset
        hm.apply_trim_preset(0, "clean_boost")
        slots = hm.get_installed_slots()
        assert slots[0]["tone"] == 55
        assert slots[0]["level"] == 80
    finally:
        hm.set_drive(orig_drive)



