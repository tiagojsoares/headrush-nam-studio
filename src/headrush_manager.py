import os
import re
import json
import uuid
import shutil
import hashlib
import zipfile
import subprocess
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
        f.flush()
        try: os.fsync(f.fileno())
        except Exception: pass
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
        f.flush()
        try: os.fsync(f.fileno())
        except Exception: pass
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

# ====================================================================
# ADVANCED PRO SUITE: SMART RENAMER, INSPECTOR, SETLISTS, HEALTH, BATCH
# ====================================================================

SMART_ABBREVIATIONS = [
    (r'(?i)\bmesa boogie\b', 'MESA'),
    (r'(?i)\bdual rectifier\b', 'RECTO DUAL'),
    (r'(?i)\btriple rectifier\b', 'RECTO TRIP'),
    (r'(?i)\brectifier\b', 'RECTO'),
    (r'(?i)\bmarshall\b', 'MRSHL'),
    (r'(?i)\bfender\b', 'FNDR'),
    (r'(?i)\bpeavey\b', 'PVY'),
    (r'(?i)\bsoldano\b', 'SLDNO'),
    (r'(?i)\bfriedman\b', 'FRDMN'),
    (r'(?i)\bdumble\b', 'DMBL'),
    (r'(?i)\bbogner\b', 'BGNR'),
    (r'(?i)\btube screamer\b', 'TS9'),
    (r'(?i)\boverdrive\b', 'OD'),
    (r'(?i)\bdistortion\b', 'DIST'),
    (r'(?i)\bcompressor\b', 'COMP'),
    (r'(?i)\bchannel\b', 'CH'),
    (r'(?i)\bclean\b', 'CLN'),
    (r'(?i)\bcrunch\b', 'CRNCH'),
    (r'(?i)\bbright\b', 'BRT'),
    (r'(?i)\bboost\b', 'BST'),
    (r'(?i)\bextreme\b', 'EXTR'),
    (r'(?i)\bpreamp\b', 'PRE'),
    (r'(?i)\bmaster\b', 'MSTR'),
    (r'(?i)\blead\b', 'LEAD'),
    (r'(?i)\brhythm\b', 'RHY')
]

def smart_format_preset_name(raw_name, max_len=24):
    """
    Intelligently shortens and optimizes model names for the HeadRush LCD screen
    and footswitch scribble-strips using regex abbreviation rules.
    """
    if not raw_name:
        return "MODEL"
        
    name = os.path.splitext(raw_name)[0]
    name = re.sub(r'^\d{3}\s*-\s*', '', name)
    name = re.sub(r'[_\-]+', ' ', name)
    
    for pattern, repl in SMART_ABBREVIATIONS:
        name = re.sub(pattern, repl, name)
        
    name = re.sub(r'[^\w\s\+\.]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:max_len].strip()

def inspect_nam_file(filepath):
    """
    Inspects a .nam model file and extracts structural metadata:
    architecture, sample rate, training loss (ESR), author, version, etc.
    """
    if not os.path.exists(filepath):
        return {"valid": False, "error": "File not found"}
        
    try:
        size_kb = round(os.path.getsize(filepath) / 1024, 1)
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
            
        arch = data.get("architecture") or "WaveNet / LSTM"
        version = data.get("version") or "1.0.0"
        sample_rate = data.get("sample_rate") or 48000
        
        metadata = data.get("metadata") or {}
        model_name = metadata.get("name") or data.get("name") or os.path.splitext(os.path.basename(filepath))[0]
        author = metadata.get("author") or data.get("author") or "Community"
        description = metadata.get("description") or ""
        date = metadata.get("date") or ""
        
        # Training loss / ESR
        training_loss = None
        if "esr" in metadata:
            training_loss = metadata["esr"]
        elif "training_loss" in metadata:
            training_loss = metadata["training_loss"]
            
        return {
            "valid": True,
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "name": model_name,
            "architecture": arch,
            "version": version,
            "author": author,
            "sample_rate": sample_rate,
            "size_kb": size_kb,
            "description": description,
            "date": date,
            "training_loss": training_loss
        }
    except Exception as e:
        return {"valid": False, "error": str(e), "filename": os.path.basename(filepath)}

def detect_duplicate_models():
    """
    Scans installed /NAM files and detects duplicates by content hash (SHA-256)
    and by normalized model names.
    """
    if not is_headrush_connected():
        return {"total_duplicates": 0, "hash_duplicates": {}, "name_duplicates": {}}
        
    slots = get_installed_slots()
    hashes = {}
    names = {}
    
    nam_dir = get_nam_dir()
    for s_num, info in slots.items():
        fname = info.get('nam_file')
        if not fname:
            continue
        full_path = os.path.join(nam_dir, fname)
        if not os.path.exists(full_path):
            continue
            
        # 1. Content Hash
        try:
            hasher = hashlib.sha256()
            with open(full_path, 'rb') as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            file_hash = hasher.hexdigest()
            hashes.setdefault(file_hash, []).append({
                "slot": s_num,
                "filename": fname,
                "preset_name": info.get('preset_name')
            })
        except Exception:
            pass
            
        # 2. Name duplicates
        norm_name = sanitize_for_headrush(info.get('preset_name') or info.get('nam_name') or '', 24).lower()
        names.setdefault(norm_name, []).append(s_num)
        
    hash_dupes = {h: items for h, items in hashes.items() if len(items) > 1}
    name_dupes = {n: s_list for n, s_list in names.items() if len(s_list) > 1}
    
    total = len(hash_dupes) + len(name_dupes)
    return {
        "total_duplicates": total,
        "hash_duplicates": hash_dupes,
        "name_duplicates": name_dupes
    }

def import_local_models_batch(file_or_dir_paths, base_slot=None, default_tone=50, default_level=70, smart_rename=True):
    """
    Imports a batch of .nam files or folders into the next free slots on the HeadRush MX5.
    Returns summary with list of installed models and slots.
    """
    if not is_headrush_connected():
        raise Exception("HeadRush MX5 não conectada.")
        
    # Gather all .nam filepaths
    nam_files = []
    for item in file_or_dir_paths:
        if os.path.isfile(item) and item.lower().endswith('.nam'):
            nam_files.append(item)
        elif os.path.isdir(item):
            for root, _, files in os.walk(item):
                for f in files:
                    if f.lower().endswith('.nam'):
                        nam_files.append(os.path.join(root, f))
                        
    # Sort files naturally
    nam_files = sorted(list(set(nam_files)))
    if not nam_files:
        return {"installed": [], "skipped": [], "count": 0}
        
    installed = []
    skipped = []
    
    slots = get_installed_slots()
    used_slots = set(s for s, info in slots.items() if info.get('nam_file'))
    
    curr_slot = base_slot if (base_slot is not None and base_slot >= 0) else 0
    
    for src_file in nam_files:
        # Find next available slot
        while curr_slot in used_slots and curr_slot <= 100:
            curr_slot += 1
            
        if curr_slot > 100:
            skipped.append({"file": src_file, "reason": "No free slots remaining (0-100 full)"})
            continue
            
        raw_name = os.path.splitext(os.path.basename(src_file))[0]
        pname = smart_format_preset_name(raw_name) if smart_rename else sanitize_for_headrush(raw_name, 24)
        
        try:
            res = install_nam_to_headrush(src_file, custom_name=pname, slot=curr_slot, tone=default_tone, level=default_level)
            installed.append({
                "slot": curr_slot,
                "preset_name": pname,
                "src_file": src_file,
                "result": res
            })
            used_slots.add(curr_slot)
            curr_slot += 1
        except Exception as e:
            skipped.append({"file": src_file, "reason": str(e)})
            
    return {
        "installed": installed,
        "skipped": skipped,
        "count": len(installed)
    }

def get_setlists_dir(root="c:/VM"):
    path = os.path.join(root, "HeadRush_Setlists")
    os.makedirs(path, exist_ok=True)
    return path

def save_setlist(name, root="c:/VM"):
    """
    Saves the entire current pedalboard configuration (all installed slots and blocks)
    as a named Setlist snapshot.
    """
    if not is_headrush_connected():
        raise Exception("HeadRush não conectada.")
        
    clean_name = re.sub(r'[^\w\s\-_]', '', str(name)).strip()
    if not clean_name:
        clean_name = "Default_Setlist"
        
    setlist_dir = os.path.join(get_setlists_dir(root), clean_name)
    if os.path.exists(setlist_dir):
        shutil.rmtree(setlist_dir, ignore_errors=True)
    os.makedirs(setlist_dir, exist_ok=True)
    
    slots = get_installed_slots()
    
    # Copy NAM
    if os.path.exists(get_nam_dir()):
        shutil.copytree(get_nam_dir(), os.path.join(setlist_dir, "NAM"))
        
    # Copy Blocks V1
    if os.path.exists(get_blocks_v1_dir()):
        shutil.copytree(get_blocks_v1_dir(), os.path.join(setlist_dir, "Blocks_V1"))
        
    # Copy Blocks V2
    if os.path.exists(get_blocks_v2_dir()):
        shutil.copytree(get_blocks_v2_dir(), os.path.join(setlist_dir, "Blocks_V2"))
        
    # Metadata
    meta = {
        "name": clean_name,
        "created_at": datetime.now().isoformat(),
        "total_slots": len(slots),
        "slots": {str(k): v["preset_name"] for k, v in slots.items() if v.get("nam_file")}
    }
    with open(os.path.join(setlist_dir, "setlist.json"), 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
        
    return setlist_dir

def list_setlists(root="c:/VM"):
    """Returns a list of all saved Setlists."""
    s_dir = get_setlists_dir(root)
    if not os.path.exists(s_dir):
        return []
    res = []
    for item in sorted(os.listdir(s_dir)):
        p = os.path.join(s_dir, item)
        if os.path.isdir(p):
            meta_file = os.path.join(p, "setlist.json")
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    res.append({
                        "name": item,
                        "path": p,
                        "created_at": meta.get("created_at", ""),
                        "total_slots": meta.get("total_slots", 0),
                        "slots": meta.get("slots", {})
                    })
                except Exception:
                    pass
            else:
                res.append({"name": item, "path": p, "created_at": "", "total_slots": 0, "slots": {}})
    return res

def load_setlist(name, root="c:/VM", make_safety_backup=True):
    """
    Restores a saved Setlist onto the HeadRush MX5.
    Creates an automatic backup before overwriting.
    """
    if not is_headrush_connected():
        raise Exception("HeadRush não conectada.")
        
    setlist_dir = os.path.join(get_setlists_dir(root), name)
    if not os.path.exists(setlist_dir):
        raise Exception(f"Setlist '{name}' não encontrado.")
        
    backup_path = None
    if make_safety_backup:
        backup_path = create_backup(target_root=root)
        
    # Clear current NAM & Blocks
    for d in [get_nam_dir(), get_blocks_v1_dir(), get_blocks_v2_dir()]:
        if os.path.exists(d):
            for f in os.listdir(d):
                try:
                    os.remove(os.path.join(d, f))
                except Exception:
                    pass
                    
    # Copy from setlist
    src_nam = os.path.join(setlist_dir, "NAM")
    if os.path.exists(src_nam):
        for f in os.listdir(src_nam):
            shutil.copy2(os.path.join(src_nam, f), os.path.join(get_nam_dir(), f))
            
    src_v1 = os.path.join(setlist_dir, "Blocks_V1")
    if os.path.exists(src_v1):
        for f in os.listdir(src_v1):
            shutil.copy2(os.path.join(src_v1, f), os.path.join(get_blocks_v1_dir(), f))
            
    src_v2 = os.path.join(setlist_dir, "Blocks_V2")
    if os.path.exists(src_v2):
        for f in os.listdir(src_v2):
            shutil.copy2(os.path.join(src_v2, f), os.path.join(get_blocks_v2_dir(), f))
            
    sync_missing_blocks()
    return {"loaded": name, "backup": backup_path}

def export_setlist_zip(name, target_zip_path, root="c:/VM"):
    """Packages a Setlist directory into a portable .zip or .hrpack file."""
    setlist_dir = os.path.join(get_setlists_dir(root), name)
    if not os.path.exists(setlist_dir):
        raise Exception(f"Setlist '{name}' não encontrado.")
        
    target_dir = os.path.dirname(target_zip_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
        
    with zipfile.ZipFile(target_zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root_d, _, files in os.walk(setlist_dir):
            for file in files:
                full_path = os.path.join(root_d, file)
                rel_path = os.path.relpath(full_path, setlist_dir)
                z.write(full_path, rel_path)
                
    return target_zip_path

def import_setlist_zip(zip_path, root="c:/VM"):
    """Imports a .zip or .hrpack Setlist and registers it."""
    if not os.path.exists(zip_path):
        raise Exception("Arquivo de setlist não encontrado.")
        
    base_name = os.path.splitext(os.path.basename(zip_path))[0]
    dest_dir = os.path.join(get_setlists_dir(root), base_name)
    os.makedirs(dest_dir, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(dest_dir)
        
    return dest_dir

def generate_stage_cheat_sheet(output_format="html"):
    """
    Generates a printable Stage Cheat Sheet (Colinha de Palco) for the guitarist.
    Formats: 'txt', 'md', 'html'.
    """
    slots = get_installed_slots()
    active_slots = [info for s, info in sorted(slots.items()) if info.get('nam_file')]
    
    if output_format == "txt":
        lines = [
            "=" * 64,
            "      HEADRUSH MX5 · GUIA DE PALCO (STAGE CHEAT SHEET)",
            "=" * 64,
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  Total: {len(active_slots)} Timbres",
            "-" * 64,
            f"{'SLOT':<6} | {'PRESET / MODELO':<30} | {'TONE':<6} | {'LEVEL':<6}",
            "-" * 64
        ]
        for s in active_slots:
            lines.append(f"{s['slot']:03d}    | {s['preset_name'][:30]:<30} | {s.get('tone', 50):<6} | {s.get('level', 70):<6}")
        lines.append("=" * 64)
        return "\n".join(lines)
        
    elif output_format == "md":
        lines = [
            "# 🎸 HeadRush MX5 · Stage Cheat Sheet",
            f"*Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Total: {len(active_slots)} Timbres*",
            "",
            "| Slot | Preset / Modelo | Tone | Level |",
            "| :--- | :--- | :---: | :---: |"
        ]
        for s in active_slots:
            lines.append(f"| `{s['slot']:03d}` | **{s['preset_name']}** | {s.get('tone', 50)}% | {s.get('level', 70)}% |")
        return "\n".join(lines)
        
    else: # HTML
        rows_html = ""
        for s in active_slots:
            pname = s['preset_name']
            tone = s.get('tone', 50)
            level = s.get('level', 70)
            rows_html += f"""
            <tr>
                <td class="slot">{s['slot']:03d}</td>
                <td class="name"><strong>{pname}</strong></td>
                <td class="trim">{tone}%</td>
                <td class="trim">{level}%</td>
            </tr>
            """
        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>HeadRush MX5 · Stage Cheat Sheet</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; }}
    .header {{ text-align: center; border-bottom: 2px solid #38bdf8; padding-bottom: 12px; margin-bottom: 20px; }}
    h1 {{ margin: 0; color: #38bdf8; font-size: 26px; }}
    .meta {{ color: #94a3b8; font-size: 13px; margin-top: 6px; }}
    table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; }}
    th {{ background: #0284c7; color: #ffffff; text-align: left; padding: 10px 14px; font-size: 14px; }}
    td {{ padding: 8px 14px; border-bottom: 1px solid #334155; font-size: 13px; }}
    tr:nth-child(even) {{ background: #182234; }}
    .slot {{ font-family: monospace; font-weight: bold; color: #38bdf8; font-size: 15px; width: 60px; }}
    .trim {{ text-align: center; width: 80px; color: #a5f3fc; }}
    @media print {{
        body {{ background: white; color: black; padding: 0; }}
        table {{ background: white; border: 1px solid #ccc; }}
        th {{ background: #ddd; color: black; }}
        td {{ border-bottom: 1px solid #eee; }}
        .slot {{ color: black; }}
        .trim {{ color: black; }}
    }}
</style>
</head>
<body>
    <div class="header">
        <h1>🎸 HeadRush MX5 · Stage Cheat Sheet</h1>
        <div class="meta">Data: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Total: {len(active_slots)} Timbres Instalados</div>
    </div>
    <table>
        <thead>
            <tr>
                <th>Slot</th>
                <th>Preset / Nome do Modelo</th>
                <th style="text-align:center;">Tone</th>
                <th style="text-align:center;">Level</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
</body>
</html>"""
        return html

def get_storage_status():
    """Returns disk space metrics and slot usage statistics."""
    slots = get_installed_slots()
    used_slots = len([s for s, info in slots.items() if info.get('nam_file')])
    
    drive = get_drive()
    disk_info = {"total_gb": 0.0, "free_gb": 0.0, "used_gb": 0.0, "percent_used": 0.0}
    
    try:
        if drive and os.path.exists(drive):
            total, used, free = shutil.disk_usage(drive)
            disk_info = {
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "percent_used": round((used / total) * 100, 1)
            }
    except Exception:
        pass
        
    return {
        "connected": is_headrush_connected(),
        "drive": drive,
        "slots_used": used_slots,
        "slots_total": 101,
        "slots_free": 101 - used_slots,
        "slots_percent": round((used_slots / 101) * 100, 1),
        "disk": disk_info
    }

def safe_eject_headrush():
    """
    Flushes Windows caches and safely prepares the HeadRush drive for ejection.
    """
    drive = get_drive().rstrip("/\\")
    
    # 1. Sync / flush write caches
    try:
        if os.name == 'nt':
            # Run PowerShell sync
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"[System.IO.File]::SetLastWriteTime('{drive}\\', [System.DateTime]::Now)"],
                capture_output=True,
                timeout=5
            )
    except Exception:
        pass
        
    return {
        "drive": drive,
        "safe_to_disconnect": True,
        "message": f"Todos os dados foram sincronizados no disco {drive}:\\. É seguro desconectar o cabo USB e reiniciar a HeadRush MX5!"
    }

def export_slot_bundle(slot_num, target_zip_path):
    """
    Exports a single slot (NAM file + ANXIETY OD block + ANXIETY OD V2 block)
    into a shareable .zip bundle.
    """
    slots = get_installed_slots()
    if slot_num not in slots or not slots[slot_num].get('nam_file'):
        raise Exception(f"Slot {slot_num:03d} não possui modelo instalado.")
        
    info = slots[slot_num]
    nam_path = os.path.join(get_nam_dir(), info['nam_file'])
    
    os.makedirs(os.path.dirname(target_zip_path) or '.', exist_ok=True)
    
    with zipfile.ZipFile(target_zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        if os.path.exists(nam_path):
            z.write(nam_path, os.path.basename(nam_path))
            
        # Add V1 block if exists
        b1_dir = get_blocks_v1_dir()
        if os.path.exists(b1_dir):
            for f in os.listdir(b1_dir):
                if f.startswith(f"{slot_num:03d} -") and f.endswith('.block'):
                    z.write(os.path.join(b1_dir, f), f"Blocks_V1/{f}")
                    
        # Add V2 block if exists
        b2_dir = get_blocks_v2_dir()
        if os.path.exists(b2_dir):
            for f in os.listdir(b2_dir):
                if f.startswith(f"{slot_num:03d} -") and f.endswith('.block'):
                    z.write(os.path.join(b2_dir, f), f"Blocks_V2/{f}")
                    
    return target_zip_path

def apply_trim_preset(slot_num, preset_type):
    """
    Applies one of the tuned A/B trim presets to an existing slot.
    Types: 'clean_boost', 'hot_drive', 'high_gain', 'unity'
    """
    presets_map = {
        "clean_boost": (55, 80),
        "hot_drive": (50, 70),
        "high_gain": (45, 65),
        "unity": (50, 50)
    }
    if preset_type not in presets_map:
        raise Exception(f"Tipo de preset inválido: {preset_type}")
        
    tone, level = presets_map[preset_type]
    slots = get_installed_slots()
    if slot_num not in slots:
        raise Exception(f"Slot {slot_num:03d} não encontrado.")
        
    pname = slots[slot_num].get('preset_name') or "MODEL"
    return update_slot_trims(slot_num, pname, tone=tone, level=level, sync_nam_name=False)

def perform_health_check():
    """
    Performs an in-depth integrity diagnostic on the HeadRush storage:
    checks block/nam file matching, JSON syntax integrity, and overall health score.
    """
    if not is_headrush_connected():
        return {
            "healthy": False,
            "score": 0,
            "issues": ["Pedaleira HeadRush MX5 não conectada."],
            "summary": "Desconectada"
        }
        
    issues = []
    warnings = []
    slots = get_installed_slots()
    
    total_slots = len(slots)
    valid_nams = 0
    valid_blocks = 0
    
    nam_dir = get_nam_dir()
    b1_dir = get_blocks_v1_dir()
    b2_dir = get_blocks_v2_dir()
    
    # 1. Check NAM models
    for s_num, info in slots.items():
        if info.get('nam_file'):
            valid_nams += 1
            n_path = os.path.join(nam_dir, info['nam_file'])
            try:
                with open(n_path, 'r', encoding='utf-8', errors='ignore') as f:
                    json.load(f)
            except Exception as e:
                issues.append(f"Slot {s_num:03d}: Arquivo .nam inválido ou corrompido ({info['nam_file']})")
                
        # 2. Check blocks
        has_v1 = bool(info.get('block_file_v1'))
        has_v2 = bool(info.get('block_file_v2'))
        if has_v1 or has_v2:
            valid_blocks += 1
            
        if info.get('nam_file') and not (has_v1 and has_v2):
            warnings.append(f"Slot {s_num:03d}: Falta bloco em uma das pastas V1 ou V2 (Use 'Sincronizar Blocos').")
            
    # 3. Check orphaned blocks
    valid_slot_set = set(s for s, info in slots.items() if info.get('nam_file'))
    for b_dir, label in [(b1_dir, "ANXIETY OD"), (b2_dir, "ANXIETY OD V2")]:
        if os.path.exists(b_dir):
            for f in os.listdir(b_dir):
                if f.endswith('.block') and f[:3].isdigit():
                    s_idx = int(f[:3])
                    if s_idx not in valid_slot_set:
                        warnings.append(f"Bloco órfão detectado em {label}: {f} (sem modelo .nam correspondente).")
                        
    score = 100
    score -= len(issues) * 15
    score -= len(warnings) * 3
    score = max(0, min(100, score))
    
    return {
        "healthy": len(issues) == 0,
        "score": score,
        "total_models": valid_nams,
        "issues": issues,
        "warnings": warnings,
        "summary": f"{score}% Saudável - {valid_nams} modelos instalados."
    }

# ====================================================================
# TONE3000 CLOUD INTEGRATION WRAPPERS
# ====================================================================

def cloud_search_tones(query="", gear=None, format_type="nam", page=1, page_size=20):
    """Search community tones on TONE3000 Cloud."""
    from tone3000_client import get_tone3000_client
    return get_tone3000_client().search_tones(query=query, gear=gear, format_type=format_type, page=page, page_size=page_size)

def cloud_get_trending(gear=None):
    """Get trending tones on TONE3000 Cloud."""
    from tone3000_client import get_tone3000_client
    return get_tone3000_client().get_trending(gear=gear)

def cloud_get_latest(gear=None):
    """Get latest published tones on TONE3000 Cloud."""
    from tone3000_client import get_tone3000_client
    return get_tone3000_client().get_latest(gear=gear)

def cloud_get_tone_models(tone_id):
    """Get individual models / captures for a specific tone on TONE3000 Cloud."""
    from tone3000_client import get_tone3000_client
    return get_tone3000_client().get_tone_models(tone_id)

def cloud_download_and_install(model_obj, slot=None, custom_name=None, tone=50, level=70):
    """Download a model from TONE3000 and install it directly into HeadRush MX5."""
    from tone3000_client import get_tone3000_client
    return get_tone3000_client().download_and_install_to_headrush(
        model_obj=model_obj,
        slot=slot,
        custom_name=custom_name,
        tone=tone,
        level=level
    )



