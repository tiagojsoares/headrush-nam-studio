import os
import re
import json
import uuid
import shutil

# Global configuration
HEADRUSH_DRIVE = "E:\\"

def get_drive():
    return HEADRUSH_DRIVE

def set_drive(drive_letter):
    global HEADRUSH_DRIVE
    HEADRUSH_DRIVE = drive_letter

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
    """Returns True if the currently set HEADRUSH_DRIVE looks like a valid HeadRush MX5 USB transfer drive."""
    drive = get_drive()
    return os.path.exists(drive) and (os.path.exists(os.path.join(drive, "Blocks")) or os.path.exists(os.path.join(drive, "Rigs")) or os.path.exists(os.path.join(drive, "NAM")))

def get_installed_slots():
    """Scans HEADRUSH_DRIVE for existing NAM models and returns a dictionary of slots."""
    slots = {}
    
    if not is_headrush_connected():
        return slots
        
    nam_dir = get_nam_dir()
    blocks_v1_dir = get_blocks_v1_dir()
    blocks_v2_dir = get_blocks_v2_dir()
    
    # 1. Scan NAM files
    if os.path.exists(nam_dir):
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
                        'preset_name': None,
                        'tone': 50,
                        'level': 70
                    }
                    
    # 2. Check Block preset files for V1
    if os.path.exists(blocks_v1_dir):
        for f in os.listdir(blocks_v1_dir):
            if f.lower().endswith('.block'):
                m = re.match(r'^(\d{3})\s*-\s*(.*)\.block$', f, re.IGNORECASE)
                if m:
                    slot_num = int(m.group(1))
                    if slot_num not in slots:
                        slots[slot_num] = {
                            'slot': slot_num, 'slot_str': f"{slot_num:03d}",
                            'nam_file': None, 'nam_name': None,
                            'block_file_v1': f, 'block_file_v2': None,
                            'preset_name': m.group(2), 'tone': 50, 'level': 70
                        }
                    else:
                        slots[slot_num]['block_file_v1'] = f
                        slots[slot_num]['preset_name'] = m.group(2)
                        
                    try:
                        with open(os.path.join(blocks_v1_dir, f), 'r', encoding='utf-8') as bfp:
                            d = json.load(bfp)
                            content = json.loads(d['content'])
                            pedal = content['data']['Anxiety OD']['children']
                            slots[slot_num]['drive'] = pedal['Drive']['value']
                            slots[slot_num]['tone'] = pedal['Tone']['value']
                            slots[slot_num]['level'] = pedal['Level']['value']
                    except Exception:
                        pass
                        
    # 3. Check Block preset files for V2 (Overrides V1 if exists, for display)
    if os.path.exists(blocks_v2_dir):
        for f in os.listdir(blocks_v2_dir):
            if f.lower().endswith('.block'):
                m = re.match(r'^(\d{3})\s*-\s*(.*)\.block$', f, re.IGNORECASE)
                if m:
                    slot_num = int(m.group(1))
                    if slot_num not in slots:
                        slots[slot_num] = {
                            'slot': slot_num, 'slot_str': f"{slot_num:03d}",
                            'nam_file': None, 'nam_name': None,
                            'block_file_v1': None, 'block_file_v2': f,
                            'preset_name': m.group(2), 'tone': 50, 'level': 70
                        }
                    else:
                        slots[slot_num]['block_file_v2'] = f
                        if not slots[slot_num]['preset_name']:
                            slots[slot_num]['preset_name'] = m.group(2)
                        
                    try:
                        with open(os.path.join(blocks_v2_dir, f), 'r', encoding='utf-8') as bfp:
                            d = json.load(bfp)
                            content = json.loads(d['content'])
                            pedal = content['data']['Anxiety OD V2']['children']
                            slots[slot_num]['drive'] = pedal['Drive']['value']
                            slots[slot_num]['tone'] = pedal['Tone']['value']
                            slots[slot_num]['level'] = pedal['Level']['value']
                    except Exception:
                        pass
                        
    return slots

def get_next_free_slot():
    slots = get_installed_slots()
    for s in range(101):
        if s not in slots or not slots[s]['nam_file']:
            return s
    return None

def sanitize_for_headrush(text, max_len=26):
    clean = re.sub(r'[^\w\s\-\+\.]', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:max_len].strip()

def create_block_preset(slot_num, preset_name, tone=50, level=70):
    """
    Generates valid HeadRush .block preset files for BOTH Anxiety OD (v1) and Anxiety OD V2.
    This guarantees resilience regardless of which mod version the user installed.
    """
    block_filename = f"{slot_num:03d} - {preset_name}.block"
    paths_created = []
    
    # Generate for V1 (Default Hijack)
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
    
    # Generate for V2 (4-Instances Mod)
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

def get_available_irs():
    ir_dir = get_ir_dir()
    if not os.path.exists(ir_dir):
        return []
        
    irs = []
    for root, dirs, files in os.walk(ir_dir):
        for f in files:
            if f.lower().endswith(('.wav', '.aif', '.aiff')):
                rel_dir = os.path.relpath(root, ir_dir)
                if rel_dir == '.':
                    folder_name = "[USER]"
                else:
                    folder_name = rel_dir.split(os.sep)[0]
                    
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
            os.remove(nam_path)
            
    # 2. Delete V1 block
    if s.get('block_file_v1'):
        b1_path = os.path.join(get_blocks_v1_dir(), s['block_file_v1'])
        if os.path.exists(b1_path):
            os.remove(b1_path)
            
    # 3. Delete V2 block
    if s.get('block_file_v2'):
        b2_path = os.path.join(get_blocks_v2_dir(), s['block_file_v2'])
        if os.path.exists(b2_path):
            os.remove(b2_path)
            
    return True

if __name__ == "__main__":
    print(f"HeadRush MX5 Connected ({HEADRUSH_DRIVE}):", is_headrush_connected())
