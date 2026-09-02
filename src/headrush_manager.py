import os
import re
import json
import uuid
import shutil
from datetime import datetime

# Global configuration
HEADRUSH_DRIVE = "E:\\"

def get_drive():
    global HEADRUSH_DRIVE
    if HEADRUSH_DRIVE and not HEADRUSH_DRIVE.endswith(("\\", "/")):
        HEADRUSH_DRIVE = HEADRUSH_DRIVE + "\\"
    return HEADRUSH_DRIVE

def set_drive(drive_letter):
    global HEADRUSH_DRIVE
    if drive_letter:
        drive_letter = drive_letter.strip().rstrip("/\\") + "\\"
    HEADRUSH_DRIVE = drive_letter

def sync_missing_blocks():
    """
    Scans the /NAM directory for all .nam files and ensures that valid .block presets
    exist in BOTH /Blocks/ANXIETY OD and /Blocks/ANXIETY OD V2.
    Returns the count of generated/repaired blocks.
    """
    if not is_headrush_connected():
        return 0
    nam_dir = get_nam_dir()
    if not os.path.exists(nam_dir):
        return 0
    generated_count = 0
    for f in sorted(os.listdir(nam_dir)):
        if f.lower().endswith('.nam'):
            m = re.match(r'^(\d{3})\s*-\s*(.*)\.nam$', f, re.IGNORECASE)
            if m:
                s_num = int(m.group(1))
                s_name = m.group(2)
                b1_dir = get_blocks_v1_dir()
                b2_dir = get_blocks_v2_dir()
                
                # Check if block exists in either folder
                b1_exists = False
                b2_exists = False
                if os.path.exists(b1_dir):
                    b1_exists = any(bf.startswith(f"{s_num:03d} -") and bf.lower().endswith('.block') for bf in os.listdir(b1_dir))
                if os.path.exists(b2_dir):
                    b2_exists = any(bf.startswith(f"{s_num:03d} -") and bf.lower().endswith('.block') for bf in os.listdir(b2_dir))
                    
                if not b1_exists or not b2_exists:
                    create_block_preset(s_num, s_name)
                    generated_count += 1
    return generated_count


def get_nam_dir():
    return os.path.join(get_drive(), "NAM")

def get_blocks_v1_dir():
    return os.path.join(get_drive(), "Blocks", "ANXIETY OD")

def get_blocks_v2_dir():
    return os.path.join(get_drive(), "Blocks", "ANXIETY OD V2")

def get_ir_dir():
    return os.path.join(get_drive(), "Impulse Responses")

def get_ir_blocks_dir():
    return os.path.join(get_drive(), "Blocks", "IR")

def is_headrush_connected():
    """Returns True if the currently set HEADRUSH_DRIVE looks like a valid HeadRush USB transfer drive."""
    drive = get_drive()
    if not drive:
        return False
    return os.path.exists(drive) and (
        os.path.exists(os.path.join(drive, "Blocks")) or 
        os.path.exists(os.path.join(drive, "Rigs")) or 
        os.path.exists(os.path.join(drive, "NAM"))
    )

def get_free_space_gb():
    """Returns available free space in GB on the HeadRush drive."""
    if not is_headrush_connected():
        return 0.0
    try:
        total, used, free = shutil.disk_usage(get_drive())
        return free / (1024 ** 3)
    except Exception:
        return 0.0

def sanitize_for_headrush(text, max_len=26):
    """Sanitizes model name for HeadRush display."""
    if not text:
        return "NAM MODEL"
    clean = re.sub(r'[^\w\s\-\+\.]', '', str(text))
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:max_len].strip()

def get_installed_slots():
    """Scans HEADRUSH_DRIVE for existing NAM models and returns a dictionary of slots (0-100)."""
    slots = {}
    
    if not is_headrush_connected():
        return slots
        
    nam_dir = get_nam_dir()
    blocks_v1_dir = get_blocks_v1_dir()
    blocks_v2_dir = get_blocks_v2_dir()
    
    # 1. Scan NAM files in /NAM
    if os.path.exists(nam_dir):
        try:
            for f in os.listdir(nam_dir):
                if f.lower().endswith('.nam'):
                    m = re.match(r'^(\d{3})\s*-\s*(.*)\.nam$', f, re.IGNORECASE)
                    if m:
                        slot_num = int(m.group(1))
                        slots[slot_num] = {
                            'slot': slot_num,
                            'slot_str': f"{slot_num:03d}",
                            'nam_file': f,
                            'nam_name': m.group(2),
                            'block_file_v1': None,
                            'block_file_v2': None,
                            'preset_name': m.group(2),
                            'drive': slot_num,
                            'tone': 50,
                            'level': 70
                        }
        except Exception:
            pass
            
    # Helper to parse block presets
    def read_blocks_folder(b_dir, v_key):
        if not os.path.exists(b_dir):
            return
        try:
            for f in os.listdir(b_dir):
                if f.lower().endswith('.block'):
                    m = re.match(r'^(\d{3})\s*-\s*(.*)\.block$', f, re.IGNORECASE)
                    if m:
                        slot_num = int(m.group(1))
                        preset_display = m.group(2)
                        
                        if slot_num not in slots:
                            slots[slot_num] = {
                                'slot': slot_num,
                                'slot_str': f"{slot_num:03d}",
                                'nam_file': None,
                                'nam_name': None,
                                'block_file_v1': None,
                                'block_file_v2': None,
                                'preset_name': preset_display,
                                'drive': slot_num,
                                'tone': 50,
                                'level': 70
                            }
                            
                        slots[slot_num][v_key] = f
                        if preset_display:
                            slots[slot_num]['preset_name'] = preset_display
                            
                        try:
                            with open(os.path.join(b_dir, f), 'r', encoding='utf-8') as bfp:
                                d = json.load(bfp)
                                content = json.loads(d['content'])
                                data_dict = content.get('data', {})
                                
                                pedal = None
                                target_key = 'Anxiety OD' if v_key == 'block_file_v1' else 'Anxiety OD V2'
                                if target_key in data_dict:
                                    pedal = data_dict[target_key].get('children')
                                else:
                                    for k, v in data_dict.items():
                                        if isinstance(v, dict) and 'children' in v:
                                            pedal = v['children']
                                            break
                                            
                                if pedal:
                                    if 'Drive' in pedal and 'value' in pedal['Drive']:
                                        slots[slot_num]['drive'] = int(pedal['Drive']['value'])
                                    if 'Tone' in pedal and 'value' in pedal['Tone']:
                                        slots[slot_num]['tone'] = int(pedal['Tone']['value'])
                                    if 'Level' in pedal and 'value' in pedal['Level']:
                                        slots[slot_num]['level'] = int(pedal['Level']['value'])
                        except Exception:
                            pass
        except Exception:
            pass

    # Read both V1 and V2 folders
    read_blocks_folder(blocks_v1_dir, 'block_file_v1')
    read_blocks_folder(blocks_v2_dir, 'block_file_v2')
    return slots

def get_next_free_slot():
    """Find the lowest available slot number between 0 and 100."""
    slots = get_installed_slots()
    for s in range(101):
        if s not in slots or not slots[s]['nam_file']:
            return s
    return None

def create_block_preset(slot_num, preset_name, tone=50, level=70):
    """
    Generates valid HeadRush .block preset files for BOTH Anxiety OD (v1) and Anxiety OD V2.
    Cleans up any preexisting blocks for this slot to avoid duplicate ghost files.
    """
    clean_name = sanitize_for_headrush(preset_name, 24)
    block_filename = f"{slot_num:03d} - {clean_name}.block"
    paths_created = []
    
    # 1. Clean up old blocks for this slot in both folders
    for b_dir in [get_blocks_v1_dir(), get_blocks_v2_dir()]:
        if os.path.exists(b_dir):
            for f in os.listdir(b_dir):
                if f.startswith(f"{slot_num:03d} -") and f.lower().endswith('.block'):
                    try:
                        os.remove(os.path.join(b_dir, f))
                    except Exception:
                        pass
                        
    # 2. Generate for V1 (Default Hijack)
    v1_dir = get_blocks_v1_dir()
    os.makedirs(v1_dir, exist_ok=True)
    v1_dest = os.path.join(v1_dir, block_filename)
    
    v1_inner = {
        "data": {
            "Anxiety OD": {
                "childorder": ["Level", "Drive", "Tone", "Hi-Lo"],
                "children": {
                    "Drive": {"type": 0, "value": int(slot_num)},
                    "Hi-Lo": {"state": False, "type": 1},
                    "Level": {"type": 0, "value": int(level)},
                    "Tone": {"type": 0, "value": int(tone)}
                }
            }
        },
        "info": {"version": "1.0.9"}
    }
    v1_block = {
        "content": json.dumps(v1_inner, separators=(',', ':')),
        "id": str(uuid.uuid4()),
        "readonly": False,
        "type": "ANXIETY OD"
    }
    with open(v1_dest, 'w', encoding='utf-8') as f:
        json.dump(v1_block, f, separators=(',', ':'))
    paths_created.append(v1_dest)
    
    # 3. Generate for V2 (4-Instances Mod)
    v2_dir = get_blocks_v2_dir()
    os.makedirs(v2_dir, exist_ok=True)
    v2_dest = os.path.join(v2_dir, block_filename)
    
    v2_inner = {
        "data": {
            "Anxiety OD V2": {
                "childorder": ["Level", "Drive", "Tone", "Hi-Lo"],
                "children": {
                    "Drive": {"type": 0, "value": int(slot_num)},
                    "Hi-Lo": {"state": False, "type": 1},
                    "Level": {"type": 0, "value": int(level)},
                    "Tone": {"type": 0, "value": int(tone)}
                }
            }
        },
        "info": {"version": "1.0.9"}
    }
    v2_block = {
        "content": json.dumps(v2_inner, separators=(',', ':')),
        "id": str(uuid.uuid4()),
        "readonly": False,
        "type": "ANXIETY OD V2"
    }
    with open(v2_dest, 'w', encoding='utf-8') as f:
        json.dump(v2_block, f, separators=(',', ':'))
    paths_created.append(v2_dest)
        
    return paths_created

def install_nam_to_headrush(src_nam_path, custom_name=None, slot=None, tone=50, level=70):
    """Installs a NAM model onto the HeadRush MX5 in the next free slot (or a specified slot)."""
    if not is_headrush_connected():
        raise Exception(f"HeadRush MX5 not detected on drive {get_drive()}")
        
    if slot is None:
        slot = get_next_free_slot()
        if slot is None:
            raise Exception("No free slots available (maximum 101 models, 0-100).")
            
    if slot < 0 or slot > 100:
        raise Exception(f"Slot {slot} out of range (0 to 100).")
        
    base_name = custom_name or os.path.splitext(os.path.basename(src_nam_path))[0]
    base_name = re.sub(r'^\d{3}\s*-\s*', '', base_name)
    
    nam_dir = get_nam_dir()
    os.makedirs(nam_dir, exist_ok=True)
    clean_nam_name = re.sub(r'[\\/*?:"<>|]', '_', base_name)
    nam_filename = f"{slot:03d} - {clean_nam_name}.nam"
    nam_dest = os.path.join(nam_dir, nam_filename)
    
    # Remove any existing NAM file in this slot
    for f in os.listdir(nam_dir):
        if f.startswith(f"{slot:03d} -") and f.lower().endswith('.nam'):
            try:
                os.remove(os.path.join(nam_dir, f))
            except Exception:
                pass
                
    shutil.copy2(src_nam_path, nam_dest)
    
    short_preset_name = sanitize_for_headrush(base_name, max_len=26)
    block_dests = create_block_preset(slot, short_preset_name, tone=tone, level=level)
    
    return {
        "slot": slot,
        "nam_path": nam_dest,
        "nam_file": nam_filename,
        "block_paths": block_dests,
        "preset_name": short_preset_name
    }

def update_slot_trims(slot_num, preset_name, tone, level, sync_nam_name=True):
    """
    Updates Tone (Input Trim), Level (Output Trim), and preset name for a slot.
    Optionally renames the .nam file to keep filenames in 100% sync.
    """
    slots = get_installed_slots()
    if slot_num not in slots:
        raise Exception(f"Slot {slot_num:03d} is not installed.")
        
    info = slots[slot_num]
    clean_preset_name = sanitize_for_headrush(preset_name, 24)
    
    # 1. Optionally rename .nam file if the name changed
    if sync_nam_name and info.get('nam_file'):
        old_nam_path = os.path.join(get_nam_dir(), info['nam_file'])
        clean_file_name = re.sub(r'[\\/*?:"<>|]', '_', clean_preset_name)
        new_nam_filename = f"{slot_num:03d} - {clean_file_name}.nam"
        new_nam_path = os.path.join(get_nam_dir(), new_nam_filename)
        
        if os.path.exists(old_nam_path) and old_nam_path != new_nam_path:
            try:
                os.rename(old_nam_path, new_nam_path)
            except Exception:
                shutil.copy2(old_nam_path, new_nam_path)
                os.remove(old_nam_path)
                
    # 2. Recreate both blocks
    create_block_preset(slot_num, clean_preset_name, tone=tone, level=level)
    return True

def move_slot(old_slot, new_slot):
    """Moves a model from old_slot to new_slot."""
    if old_slot == new_slot:
        return True
    if new_slot < 0 or new_slot > 100:
        raise Exception(f"Slot {new_slot} out of range (0-100).")
        
    slots = get_installed_slots()
    if old_slot not in slots:
        raise Exception(f"Slot {old_slot:03d} does not exist.")
        
    info = slots[old_slot]
    if not info.get('nam_file'):
        raise Exception(f"Slot {old_slot:03d} has no .nam file.")
        
    old_nam_path = os.path.join(get_nam_dir(), info['nam_file'])
    tone = info.get('tone', 50)
    level = info.get('level', 70)
    pname = info.get('preset_name') or info.get('nam_name') or "MODEL"
    
    # Delete new_slot if occupied
    if new_slot in slots:
        delete_slot(new_slot)
        
    # Install to new_slot
    install_nam_to_headrush(old_nam_path, custom_name=pname, slot=new_slot, tone=tone, level=level)
    
    # Delete old slot
    delete_slot(old_slot)
    return True

def delete_slot(slot_num):
    """Deletes NAM file and corresponding block presets for a given slot."""
    slots = get_installed_slots()
    if slot_num not in slots:
        return False
        
    s = slots[slot_num]
    
    # 1. Delete .nam file
    if s.get('nam_file'):
        nam_path = os.path.join(get_nam_dir(), s['nam_file'])
        if os.path.exists(nam_path):
            try: os.remove(nam_path)
            except Exception: pass
            
    # 2. Delete all blocks for this slot
    for b_dir in [get_blocks_v1_dir(), get_blocks_v2_dir()]:
        if os.path.exists(b_dir):
            for f in os.listdir(b_dir):
                if f.startswith(f"{slot_num:03d} -") and f.lower().endswith('.block'):
                    try: os.remove(os.path.join(b_dir, f))
                    except Exception: pass
                    
    return True

def get_available_irs():
    """Returns a list of all IR files found in /Impulse Responses grouped by directory."""
    ir_dir = get_ir_dir()
    if not os.path.exists(ir_dir):
        return []
        
    irs = []
    for root, dirs, files in os.walk(ir_dir):
        for f in files:
            if f.lower().endswith(('.wav', '.aif', '.aiff')):
                rel_dir = os.path.relpath(root, ir_dir)
                folder_name = "[USER]" if rel_dir == '.' else rel_dir.split(os.sep)[0]
                name_without_ext = os.path.splitext(f)[0]
                irs.append({
                    "folder": folder_name,
                    "filename": f,
                    "name": name_without_ext,
                    "rel_path": os.path.relpath(os.path.join(root, f), ir_dir),
                    "ir_string": f"[directory]({folder_name})[name]({name_without_ext})"
                })
    return irs

def create_ir_block_preset(preset_name, ir_folder, ir_name, gain=-10.0, hi_cut=10000, lo_cut=50):
    """Generates an IR .block preset in /Blocks/IR."""
    ir_blocks_dir = get_ir_blocks_dir()
    os.makedirs(ir_blocks_dir, exist_ok=True)
    block_filename = f"{sanitize_for_headrush(preset_name, 26)}.block"
    dest_path = os.path.join(ir_blocks_dir, block_filename)
    
    ir_ref_string = f"[directory]({ir_folder})[name]({ir_name})"
    
    inner_data = {
        "data": {
            "IR": {
                "childorder": ["DoubleStates", "IR", "Gain", "HiCut", "LoCut", "Mix"],
                "children": {
                    "DoubleStates": {"state": False, "type": 3},
                    "Gain": {"type": 0, "value": float(gain)},
                    "HiCut": {"type": 0, "value": int(hi_cut)},
                    "IR": {"string": ir_ref_string, "type": 8},
                    "LoCut": {"type": 0, "value": int(lo_cut)},
                    "Mix": {"type": 0, "value": 100}
                }
            }
        },
        "info": {"version": "1.0.9"}
    }
    
    block_obj = {
        "content": json.dumps(inner_data, separators=(',', ':')),
        "id": str(uuid.uuid4()),
        "readonly": False,
        "type": "IR"
    }
    
    with open(dest_path, 'w', encoding='utf-8') as f:
        json.dump(block_obj, f, separators=(',', ':'))
        
    return dest_path

def create_backup(target_root="c:/VM"):
    """Creates a timestamped backup of the connected HeadRush storage."""
    if not is_headrush_connected():
        raise Exception("HeadRush is not connected.")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(target_root, f"HeadRush_Backup_{ts}")
    os.makedirs(backup_dir, exist_ok=True)
    
    if os.path.exists(get_nam_dir()):
        shutil.copytree(get_nam_dir(), os.path.join(backup_dir, "NAM"))
    if os.path.exists(get_blocks_v1_dir()):
        shutil.copytree(get_blocks_v1_dir(), os.path.join(backup_dir, "Blocks_ANXIETY_OD"))
    if os.path.exists(get_blocks_v2_dir()):
        shutil.copytree(get_blocks_v2_dir(), os.path.join(backup_dir, "Blocks_ANXIETY_OD_V2"))
    return backup_dir

def list_backups(target_root="c:/VM"):
    """Returns a list of all existing backup directories."""
    if not os.path.exists(target_root):
        return []
    backups = []
    for d in os.listdir(target_root):
        if d.startswith("HeadRush_Backup_") and os.path.isdir(os.path.join(target_root, d)):
            backups.append({
                "name": d,
                "path": os.path.join(target_root, d)
            })
    return sorted(backups, key=lambda x: x['name'], reverse=True)

def restore_backup(backup_dir):
    """Restores a backup directory to the HeadRush drive."""
    if not is_headrush_connected():
        raise Exception("HeadRush is not connected.")
    if not os.path.exists(backup_dir):
        raise Exception(f"Backup directory not found: {backup_dir}")
        
    # Restore NAM
    src_nam = os.path.join(backup_dir, "NAM")
    if os.path.exists(src_nam):
        dest_nam = get_nam_dir()
        os.makedirs(dest_nam, exist_ok=True)
        for f in os.listdir(dest_nam):
            try: os.remove(os.path.join(dest_nam, f))
            except Exception: pass
        for f in os.listdir(src_nam):
            shutil.copy2(os.path.join(src_nam, f), os.path.join(dest_nam, f))
            
    # Restore Blocks V1
    src_b1 = os.path.join(backup_dir, "Blocks_ANXIETY_OD")
    if os.path.exists(src_b1):
        dest_b1 = get_blocks_v1_dir()
        os.makedirs(dest_b1, exist_ok=True)
        for f in os.listdir(src_b1):
            shutil.copy2(os.path.join(src_b1, f), os.path.join(dest_b1, f))
            
    # Restore Blocks V2
    src_b2 = os.path.join(backup_dir, "Blocks_ANXIETY_OD_V2")
    if os.path.exists(src_b2):
        dest_b2 = get_blocks_v2_dir()
        os.makedirs(dest_b2, exist_ok=True)
        for f in os.listdir(src_b2):
            shutil.copy2(os.path.join(src_b2, f), os.path.join(dest_b2, f))
            
    return True

def clean_orphaned_blocks():
    """
    Deletes any numbered .block preset in /Blocks/ANXIETY OD and /Blocks/ANXIETY OD V2
    that does not have a corresponding .nam model file in /NAM.
    Preserves default factory presets (+DEFAULT.block, etc.).
    """
    if not is_headrush_connected():
        return []
    slots = get_installed_slots()
    valid_slots = set(s for s, info in slots.items() if info.get('nam_file'))
    
    deleted = []
    for b_dir in [get_blocks_v1_dir(), get_blocks_v2_dir()]:
        if os.path.exists(b_dir):
            for f in os.listdir(b_dir):
                if f.lower().endswith('.block'):
                    m = re.match(r'^(\d{3})\s*-\s*(.*)\.block$', f, re.IGNORECASE)
                    if m:
                        slot_num = int(m.group(1))
                        if slot_num not in valid_slots:
                            try:
                                os.remove(os.path.join(b_dir, f))
                                deleted.append(f)
                            except Exception:
                                pass
    return deleted

def defrag_and_reorder_slots(sort_by="current", make_safety_backup=True):
    """
    Reorganizes all installed NAM models into sequential slots (000 to N-1).
    - sort_by: 'current' (preserves order, compacts gaps) or 'alpha' (alphabetical sort).
    - make_safety_backup: Automatically creates a full backup before modifying files.
    """
    if not is_headrush_connected():
        raise Exception("HeadRush MX5 não está conectada.")
        
    slots = get_installed_slots()
    active_models = [info for s, info in slots.items() if info.get('nam_file')]
    
    if not active_models:
        return {"count": 0, "backup": None, "mode": sort_by}
        
    # 1. Safety Backup
    backup_path = None
    if make_safety_backup:
        backup_path = create_backup()
        
    # 2. Sort active models
    if sort_by == "alpha":
        active_models.sort(key=lambda x: sanitize_for_headrush(x.get('nam_name') or x.get('preset_name') or '').lower())
    else:
        active_models.sort(key=lambda x: x['slot'])
        
    nam_dir = get_nam_dir()
    
    # 3. Stage models into temporary folder
    import tempfile
    temp_stage = tempfile.mkdtemp(prefix="headrush_organize_")
    
    try:
        staged_items = []
        for new_idx, info in enumerate(active_models):
            old_nam_path = os.path.join(nam_dir, info['nam_file'])
            if not os.path.exists(old_nam_path):
                continue
                
            clean_name = sanitize_for_headrush(info.get('nam_name') or info.get('preset_name') or f"MODEL {new_idx:03d}", 24)
            clean_file_name = re.sub(r'[\\/*?:"<>|]', '_', clean_name)
            new_nam_filename = f"{new_idx:03d} - {clean_file_name}.nam"
            staged_nam_path = os.path.join(temp_stage, new_nam_filename)
            
            shutil.copy2(old_nam_path, staged_nam_path)
            
            staged_items.append({
                "new_slot": new_idx,
                "preset_name": clean_name,
                "tone": info.get('tone', 50),
                "level": info.get('level', 70),
                "staged_path": staged_nam_path,
                "filename": new_nam_filename
            })
            
        # 4. Clear existing /NAM directory of .nam files
        for f in os.listdir(nam_dir):
            if f.lower().endswith('.nam'):
                try:
                    os.remove(os.path.join(nam_dir, f))
                except Exception:
                    pass
                    
        # 5. Clear all existing numbered .block files in V1 and V2
        for b_dir in [get_blocks_v1_dir(), get_blocks_v2_dir()]:
            if os.path.exists(b_dir):
                for f in os.listdir(b_dir):
                    if f.lower().endswith('.block') and f[:3].isdigit():
                        try:
                            os.remove(os.path.join(b_dir, f))
                        except Exception:
                            pass
                            
        # 6. Copy back all renumbered .nam files & generate fresh .blocks
        for item in staged_items:
            dest_nam = os.path.join(nam_dir, item['filename'])
            shutil.copy2(item['staged_path'], dest_nam)
            create_block_preset(item['new_slot'], item['preset_name'], tone=item['tone'], level=item['level'])
            
        return {
            "count": len(staged_items),
            "backup": backup_path,
            "mode": sort_by
        }
    finally:
        shutil.rmtree(temp_stage, ignore_errors=True)

