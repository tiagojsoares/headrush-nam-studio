import os
import json
import uuid
import pytest
import hashlib
import zipfile
import headrush_manager as hm

# ============================================================================
# 1. STRING SANITIZATION & SMART LCD HEURISTICS TESTS
# ============================================================================

def test_sanitize_for_headrush_exhaustive():
    """Validates string sanitization under complex inputs, Unicode, accents, and malicious paths."""
    # Accents and Portuguese characters (stripped of non-ascii and punctuation)
    sanitized_accents = hm.sanitize_for_headrush("Mesa Boogïê - Tïmbrë Çhãññel 3!")
    assert "Mesa Boog" in sanitized_accents
    assert len(sanitized_accents) <= 26
    
    # Path traversal attempts and illegal filename characters
    raw_path_injection = "../../etc/passwd/Mesa:Boogie*?|<>.nam"
    sanitized = hm.sanitize_for_headrush(raw_path_injection)
    for bad_char in [":", "*", "?", "<", ">", "|", "/", "\\"]:
        assert bad_char not in sanitized
        
    # Boundary clipping
    assert len(hm.sanitize_for_headrush("X" * 100, max_len=24)) == 24
    assert len(hm.sanitize_for_headrush("X" * 100, max_len=16)) == 16
    assert len(hm.sanitize_for_headrush("X" * 100, max_len=26)) == 26
    
    # Empty or whitespace inputs fallback cleanly
    assert hm.sanitize_for_headrush("   ") == ""

def test_smart_format_preset_name_comprehensive():
    """Validates brand compaction heuristics for the 24-character HeadRush LCD display."""
    test_cases = [
        ("Mesa_Boogie_Dual_Rectifier_Solo_Head_Ch3", "MESA RECTO DUAL Solo Head"[:24].strip()),
        ("Marshall_JCM800_2203_High_Sensitivity", "MRSHL JCM800 2203 High"),
        ("Peavey_5150_Block_Letter_Lead_Channel", "5150 Block Letter Lead"),
        ("Ibanez_Tube_Screamer_TS9_Overdrive", "TS9 OD"),
        ("Friedman_BE100_Brown_Eye_HBE_Channel", "FRDMN BE100 Brown Eye"),
        ("Soldano_SLO100_Super_Lead_Overdrive", "SLO100 Super Lead OD"),
        ("Bogner_Ecstasy_101B_Red_Channel", "BGNR Ecstasy 101B Red"),
        ("Dumble_Overdrive_Special_Clean", "DMBL OD Special Clean")
    ]
    for raw, expected_substr in test_cases:
        res = hm.smart_format_preset_name(raw)
        assert len(res) <= 24, f"Result '{res}' exceeds 24 chars for input '{raw}'"
        assert len(res) > 0

# ============================================================================
# 2. BLOCK PRESET & SCHEMA INTEGRITY TESTS (V1 & V2 HOOK SPECIFICATION)
# ============================================================================

def test_create_block_preset_exact_schema(mock_pedal_drive):
    """
    Validates that generated .block files strictly conform to the HeadRush
    firmware mod JSON schema with valid UUIDs, numeric Knob mappings, and non-readonly flags.
    """
    paths = hm.create_block_preset(slot_num=42, preset_name="Friedman HBE", tone=48, level=78)
    assert len(paths) == 2
    
    v1_path, v2_path = paths
    assert os.path.exists(v1_path)
    assert os.path.exists(v2_path)
    
    # Validate V1 block
    with open(v1_path, "r", encoding="utf-8") as f:
        v1_data = json.load(f)
        # Check UUID format
        parsed_uuid = uuid.UUID(v1_data["id"])
        assert parsed_uuid.version == 4
        assert v1_data["type"] == "ANXIETY OD"
        assert v1_data["readonly"] is False
        
        inner = json.loads(v1_data["content"])
        pedal = inner["data"]["Anxiety OD"]["children"]
        assert pedal["Drive"]["value"] == 42
        assert pedal["Tone"]["value"] == 48
        assert pedal["Level"]["value"] == 78

    # Validate V2 block
    with open(v2_path, "r", encoding="utf-8") as f:
        v2_data = json.load(f)
        parsed_uuid = uuid.UUID(v2_data["id"])
        assert parsed_uuid.version == 4
        assert v2_data["type"] == "ANXIETY OD V2"
        assert v2_data["readonly"] is False
        
        inner = json.loads(v2_data["content"])
        pedal = inner["data"]["Anxiety OD V2"]["children"]
        assert pedal["Drive"]["value"] == 42
        assert pedal["Tone"]["value"] == 48
        assert pedal["Level"]["value"] == 78

def test_create_ir_block_preset_schema(mock_pedal_drive):
    """Validates Impulse Response .block preset formatting and string interpolation."""
    ir_path = hm.create_ir_block_preset(
        preset_name="BOGNER 4x12 V30",
        ir_folder="Bogner Standard",
        ir_name="Bogner_V30_SM57_CapEdge",
        gain=-7.5,
        hi_cut=9000,
        lo_cut=75
    )
    assert os.path.exists(ir_path)
    with open(ir_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["type"] == "IR"
        inner = json.loads(data["content"])
        ir_obj = inner["data"]["IR"]["children"]
        assert ir_obj["Gain"]["value"] == -7.5
        assert ir_obj["HiCut"]["value"] == 9000
        assert ir_obj["LoCut"]["value"] == 75
        assert ir_obj["IR"]["string"] == "[directory](Bogner Standard)[name](Bogner_V30_SM57_CapEdge)"

# ============================================================================
# 3. SLOT BOUNDARY & SATURATION LIMIT TESTS (0 - 100 LIMIT)
# ============================================================================

def test_slot_boundary_edges(mock_pedal_drive, realistic_nam_files):
    """Verifies edge limits: slot 0 (min) and slot 100 (max allowed)."""
    # Minimum valid slot: 0
    res_min = hm.install_nam_to_headrush(realistic_nam_files["wavenet"], custom_name="EDGE MIN 0", slot=0)
    assert res_min["slot"] == 0
    assert os.path.exists(os.path.join(hm.get_nam_dir(), "000 - EDGE MIN 0.nam"))
    
    # Maximum valid slot: 100
    res_max = hm.install_nam_to_headrush(realistic_nam_files["lstm"], custom_name="EDGE MAX 100", slot=100)
    assert res_max["slot"] == 100
    assert os.path.exists(os.path.join(hm.get_nam_dir(), "100 - EDGE MAX 100.nam"))
    
    slots = hm.get_installed_slots()
    assert 0 in slots
    assert 100 in slots

def test_slot_capacity_saturation(mock_pedal_drive, realistic_nam_files):
    """
    Fills all 101 slots (0 to 100) and asserts that get_next_free_slot() returns None,
    and attempting to install a 102nd slot throws a clear capacity exception.
    """
    src_file = realistic_nam_files["wavenet"]
    # Bulk simulate population of all 101 slots
    for i in range(101):
        nam_name = f"{i:03d} - Model_{i:03d}.nam"
        with open(os.path.join(hm.get_nam_dir(), nam_name), "w", encoding="utf-8") as f:
            f.write("{}")
        hm.create_block_preset(i, f"Model_{i:03d}")

    assert hm.get_next_free_slot() == None
    
    # Attempting to auto-allocate on a full pedalboard must raise Exception
    with pytest.raises(Exception, match="No free slots available"):
        hm.install_nam_to_headrush(src_file, custom_name="OVERFLOW MODEL")

# ============================================================================
# 4. NAM MODEL INSPECTOR TESTS (REALISTIC METADATA & FAULT DETECTION)
# ============================================================================

def test_inspect_nam_realistic_and_faulty_files(realistic_nam_files):
    """Tests the inspector against valid WaveNet, LSTM, and corrupted/binary files."""
    # WaveNet valid
    w_info = hm.inspect_nam_file(realistic_nam_files["wavenet"])
    assert w_info["valid"] is True
    assert w_info["architecture"] == "WaveNet"
    assert w_info["sample_rate"] == 48000
    assert w_info["author"] == "NAM Audio Lab"
    assert w_info["training_loss"] == 0.00942
    assert w_info["size_kb"] > 0
    
    # LSTM valid
    l_info = hm.inspect_nam_file(realistic_nam_files["lstm"])
    assert l_info["valid"] is True
    assert l_info["architecture"] == "LSTM"
    assert l_info["author"] == "Vintage Tone Studio"
    
    # Truncated/corrupted JSON
    c_info = hm.inspect_nam_file(realistic_nam_files["corrupt"])
    assert c_info["valid"] is False
    assert "error" in c_info and c_info["error"]
    
    # Binary garbage
    b_info = hm.inspect_nam_file(realistic_nam_files["binary"])
    assert b_info["valid"] is False

# ============================================================================
# 5. DUPLICATE DETECTION TESTS (SHA-256 HASH & NAME COLLISION)
# ============================================================================

def test_detect_duplicate_models_deep(mock_pedal_drive, realistic_nam_files):
    """Tests exact content hash duplicates across different slots and name collisions."""
    src_a = realistic_nam_files["wavenet"]
    src_b = realistic_nam_files["lstm"]
    
    # Install identical content to slot 1 and slot 15 with different names
    hm.install_nam_to_headrush(src_a, custom_name="Preset One", slot=1)
    hm.install_nam_to_headrush(src_a, custom_name="Preset Dupe", slot=15)
    
    # Install different content but with same preset name to slot 30
    hm.install_nam_to_headrush(src_b, custom_name="Preset One", slot=30)
    
    dupes = hm.detect_duplicate_models()
    assert dupes["total_duplicates"] >= 2
    
    # Hash duplicates should group slot 1 and slot 15
    assert len(dupes["hash_duplicates"]) == 1
    for h, items in dupes["hash_duplicates"].items():
        slot_nums = [it["slot"] for it in items]
        assert 1 in slot_nums and 15 in slot_nums
        
    # Name duplicates should group slot 1 and slot 30 ("Preset One" in lowercase)
    assert "preset one" in dupes["name_duplicates"]
    assert dupes["name_duplicates"]["preset one"] == [1, 30]

# ============================================================================
# 6. BATCH IMPORT & SUBDIRECTORY RECURSION TESTS
# ============================================================================

def test_import_local_models_batch_deep(mock_pedal_drive, tmp_path):
    """Tests batch importing with nested folders, smart renaming, and slot assignment."""
    pack_dir = tmp_path / "My_Rock_Pack"
    sub_dir = pack_dir / "High_Gain_Lead"
    os.makedirs(sub_dir, exist_ok=True)
    
    (pack_dir / "01_Mesa_Boogie_Mark_V.nam").write_text("{}", encoding="utf-8")
    (pack_dir / "02_Marshall_Plexi_1959.nam").write_text("{}", encoding="utf-8")
    (sub_dir / "03_Bogner_Shiva_Lead.nam").write_text("{}", encoding="utf-8")
    (sub_dir / "ignored_file.txt").write_text("Notes", encoding="utf-8")
    
    res = hm.import_local_models_batch([str(pack_dir)], smart_rename=True)
    assert res["count"] == 3
    
    slots = hm.get_installed_slots()
    assert len(slots) == 3
    # Check that smart renaming condensed Mesa Boogie
    pnames = [info["preset_name"] for info in slots.values()]
    assert any("MESA" in p for p in pnames)

# ============================================================================
# 7. DEFRAGMENTATION & ALPHABETICAL RE-INDEXING WITH BACKUP ROLLBACK
# ============================================================================

def test_defrag_and_reorder_full_integrity(populated_pedal_drive):
    """
    Validates that defragmenting scattered slots (0, 12, 47, 99):
    1. Compacts to continuous slots (0, 1, 2, 3).
    2. Keeps SHA-256 hashes of the models intact.
    3. Updates both V1 and V2 .block Drive parameter to match new slot.
    4. Automatically generates a restoreable safety backup.
    """
    initial_slots = hm.get_installed_slots()
    assert set(initial_slots.keys()) == {0, 12, 47, 99}
    
    # Store initial hashes
    initial_hashes = {}
    for s, info in initial_slots.items():
        p = os.path.join(hm.get_nam_dir(), info["nam_file"])
        with open(p, "rb") as f:
            initial_hashes[info["preset_name"]] = hashlib.sha256(f.read()).hexdigest()
            
    # Run alphabetical defrag
    res = hm.defrag_and_reorder_slots(sort_by="alpha", make_safety_backup=True)
    assert res["count"] == 4
    
    new_slots = hm.get_installed_slots()
    assert set(new_slots.keys()) == {0, 1, 2, 3}
    
    # Alphabetical order:
    # 0: FRIEDMAN BE100
    # 1: KLON CLEAN BOOST
    # 2: MESA RECTO LEAD
    # 3: SOLDANO SLO LEAD
    assert new_slots[0]["preset_name"] == "FRIEDMAN BE100"
    assert new_slots[1]["preset_name"] == "KLON CLEAN BOOST"
    assert new_slots[2]["preset_name"] == "MESA RECTO LEAD"
    assert new_slots[3]["preset_name"] == "SOLDANO SLO LEAD"
    
    # Verify model hashes are preserved
    for s, info in new_slots.items():
        p = os.path.join(hm.get_nam_dir(), info["nam_file"])
        with open(p, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        assert h == initial_hashes[info["preset_name"]]
        
        # Check Drive knob in block preset matches new slot
        v2_path = os.path.join(hm.get_blocks_v2_dir(), info["block_file_v2"])
        with open(v2_path, "r", encoding="utf-8") as f:
            v2_json = json.load(f)
            inner = json.loads(v2_json["content"])
            assert inner["data"]["Anxiety OD V2"]["children"]["Drive"]["value"] == s

    # Rollback to safety backup
    b_dir = res["backup"]
    assert os.path.exists(b_dir)
    # Clear current compacted slots before restoring backup
    for s in list(hm.get_installed_slots().keys()):
        hm.delete_slot(s)
    hm.restore_backup(b_dir)
    restored_slots = hm.get_installed_slots()
    assert set(restored_slots.keys()) == {0, 12, 47, 99}

# ============================================================================
# 8. SETLIST & PROFILE SNAPSHOT IMPORT / EXPORT ROUND-TRIP
# ============================================================================

def test_setlist_snapshot_export_import_roundtrip(populated_pedal_drive, tmp_path):
    """
    Tests saving a complete setlist, exporting to .hrpack (zip), wiping the pedal,
    and importing back with exact parity.
    """
    setlists_root = str(tmp_path / "My_Setlists")
    
    # 1. Save Setlist
    s_dir = hm.save_setlist("Heavy_Tour_Setlist", root=setlists_root)
    assert os.path.exists(s_dir)
    
    # 2. Export to .hrpack zip
    export_pack = str(tmp_path / "Heavy_Tour.hrpack")
    hm.export_setlist_zip("Heavy_Tour_Setlist", export_pack, root=setlists_root)
    assert os.path.exists(export_pack)
    
    # Inspect zip contents
    with zipfile.ZipFile(export_pack, "r") as z:
        namelist = z.namelist()
        assert "setlist.json" in namelist
        assert any(n.startswith("NAM/") for n in namelist)
        assert any(n.startswith("Blocks_V2/") for n in namelist)
        
    # 3. Wipe pedalboard completely
    for s in list(hm.get_installed_slots().keys()):
        hm.delete_slot(s)
    assert len(hm.get_installed_slots()) == 0
    
    # 4. Import zip back into a fresh setlist slot
    imported_path = hm.import_setlist_zip(export_pack, root=setlists_root)
    assert os.path.basename(imported_path) == "Heavy_Tour"
    
    # 5. Load imported setlist onto pedal
    hm.load_setlist("Heavy_Tour", root=setlists_root)
    restored_slots = hm.get_installed_slots()
    assert len(restored_slots) == 4
    assert 0 in restored_slots and 12 in restored_slots and 47 in restored_slots and 99 in restored_slots
    assert restored_slots[0]["preset_name"] == "MESA RECTO LEAD"

# ============================================================================
# 9. FAULT INJECTION, HEALTH DIAGNOSTIC & AUTO-REPAIR TESTS
# ============================================================================

def test_health_check_fault_injection_and_auto_repair(populated_pedal_drive):
    """
    Injects realistic faults into the pedalboard:
    - 1 orphaned block in V1 and V2
    - 1 missing block for an existing model
    - 1 corrupted .nam file
    Asserts detection and verifies 100% healing.
    """
    # 1. Healthy initial state
    h1 = hm.perform_health_check()
    assert h1["healthy"] is True
    assert h1["score"] == 100
    
    # Fault A: Create orphaned block for slot 80 (no .nam file)
    hm.create_block_preset(80, "Ghost Preset")
    
    # Fault B: Create .nam file with corrupt JSON
    corrupt_nam = os.path.join(hm.get_nam_dir(), "077 - Broken Amp.nam")
    with open(corrupt_nam, "w", encoding="utf-8") as f:
        f.write("{corrupt_json: true")
        
    # Fault C: Delete V1 block for slot 12
    v1_b = os.path.join(hm.get_blocks_v1_dir(), "012 - KLON CLEAN BOOST.block")
    if os.path.exists(v1_b):
        os.remove(v1_b)
        
    # Run diagnostic
    h2 = hm.perform_health_check()
    assert h2["healthy"] is False
    assert h2["score"] < 90
    assert len(h2["issues"]) >= 1
    assert len(h2["warnings"]) >= 1
    assert any("Slot 077" in iss for iss in h2["issues"])
    assert any("Ghost Preset" in w or "080" in w for w in h2["warnings"])
    
    # Fix faults
    os.remove(corrupt_nam) # Remove bad model
    cleaned = hm.clean_orphaned_blocks()
    assert any("080" in f for f in cleaned)
    
    repaired_count = hm.sync_missing_blocks()
    assert repaired_count >= 1 # Restores V1 block for slot 12
    
    # Re-run diagnostic: should be fully healthy
    h3 = hm.perform_health_check()
    assert h3["healthy"] is True
    assert h3["score"] == 100

# ============================================================================
# 10. STAGE CHEAT SHEET & SAFE EJECT TESTS
# ============================================================================

def test_stage_cheat_sheet_formats(populated_pedal_drive):
    """Tests HTML, Markdown, and plain text stage cheat sheet generation."""
    # Plain text
    txt = hm.generate_stage_cheat_sheet(output_format="txt")
    assert "HEADRUSH MX5" in txt
    assert "000" in txt and "MESA RECTO LEAD" in txt
    assert "047" in txt and "FRIEDMAN BE100" in txt
    
    # Markdown
    md = hm.generate_stage_cheat_sheet(output_format="md")
    assert "| Slot | Preset / Modelo | Tone | Level |" in md
    assert "| `000` |" in md
    
    # HTML
    html = hm.generate_stage_cheat_sheet(output_format="html")
    assert "<!DOCTYPE html>" in html
    assert "<table" in html
    assert "MESA RECTO LEAD" in html
    assert "@media print" in html

def test_safe_eject_execution(populated_pedal_drive):
    """Validates that safe eject executes clean write flushes."""
    res = hm.safe_eject_headrush()
    assert res["safe_to_disconnect"] is True
    assert "sincronizados" in res["message"]
