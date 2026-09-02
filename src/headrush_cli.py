import sys
import os
import shutil
import argparse
from datetime import datetime
import headrush_manager as hm
import sqlite3

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

DB_PATH = "c:/VM/TONE3000_NAM_Library/tone3000.db"
LIBRARY_DIR = "c:/VM/TONE3000_NAM_Library"

def cmd_list(args):
    print("\n=======================================================")
    print(" 🎸 HEADRUSH MX5 · INSTALLED NAM MODELS & BLOCK PRESETS")
    print("=======================================================")
    if not hm.is_headrush_connected():
        print("[!] HeadRush MX5 drive E: not detected.")
        return
        
    slots = hm.get_installed_slots()
    print(f"Total slots occupied: {len(slots)} / 101 (Next free: {hm.get_next_free_slot():03d})\n")
    print(f"{'SLOT':<6} {'DRIVE':<7} {'TONE':<6} {'LEVEL':<7} {'PRESET NAME':<26} {'NAM MODEL FILE'}")
    print("-" * 90)
    for s in sorted(slots.keys()):
        info = slots[s]
        slot_str = info['slot_str']
        dr = str(info.get('drive', s))
        tn = str(info.get('tone', 50))
        lv = str(info.get('level', 70))
        pname = info.get('preset_name') or "(No block preset)"
        nfile = info.get('nam_file') or "(No .nam file)"
        print(f"{slot_str:<6} {dr:<7} {tn:<6} {lv:<7} {pname:<26} {nfile}")

def cmd_install(args):
    if not hm.is_headrush_connected():
        print("[!] HeadRush MX5 drive E: not detected.")
        return
        
    nam_path = args.path
    if not os.path.isabs(nam_path):
        nam_path = os.path.join(LIBRARY_DIR, nam_path)
        
    if not os.path.exists(nam_path):
        print(f"[!] File not found: {nam_path}")
        return
        
    slot = args.slot
    name = args.name
    tone = args.tone
    level = args.level
    
    print(f"Installing '{os.path.basename(nam_path)}' to HeadRush MX5...")
    res = hm.install_nam_to_headrush(nam_path, custom_name=name, slot=slot, tone=tone, level=level)
    print(f"[OK] Successfully installed to slot {res['slot']:03d}!")
    print(f"  NAM File:   {res['nam_file']}")
    print(f"  Preset:     {res['preset_name']}.block (Drive={res['slot']}, Tone={tone}, Level={level})")
    print(f"  Block Path: {res['block_path']}")

def cmd_search(args):
    q = args.query
    arch_filter = getattr(args, 'arch', 'all')
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    sql = '''
        SELECT m.id, m.name, t.title, COALESCE(u.username, u.display_name, 'Community'), m.architecture_version, m.local_path
        FROM models_fts fts
        JOIN models m ON fts.model_id = m.id
        JOIN tones t ON m.tone_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE models_fts MATCH ?
    '''
    params = [f'"{q}"*']
    if arch_filter and arch_filter != 'all':
        sql += ' AND m.architecture_version = ?'
        params.append(arch_filter)
        
    sql += ' LIMIT 20'
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    
    print(f"\nSearch results for '{q}' [Arch: {arch_filter}] ({len(rows)} shown):")
    print("-" * 90)
    for r in rows:
        m_id, m_name, t_title, creator, arch, lpath = r
        arch_tag = "[A2]" if arch == '2' else "[v1]"
        print(f"ID {m_id:6d} | {arch_tag:<4} | {m_name:<30} | Pack: {t_title:<25} | By: {creator}")
        print(f"   Path: {lpath}")

def cmd_irs(args):
    if not hm.is_headrush_connected():
        print("[!] HeadRush MX5 drive E: not detected.")
        return
        
    irs = hm.get_available_irs()
    print(f"\nFound {len(irs)} Impulse Responses on HeadRush MX5 (E:/Impulse Responses):")
    
    folders = {}
    for ir in irs:
        folders[ir['folder']] = folders.get(ir['folder'], 0) + 1
        
    print(f"Grouped into {len(folders)} folders:")
    for f, cnt in sorted(folders.items(), key=lambda x: x[1], reverse=True):
        print(f"  📁 {f:<40} ({cnt} IRs)")

def cmd_backup(args):
    if not hm.is_headrush_connected():
        print("[!] HeadRush MX5 drive E: not detected.")
        return
        
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = f"c:/VM/HeadRush_Backup_{ts}"
    os.makedirs(backup_root, exist_ok=True)
    
    if os.path.exists(hm.get_nam_dir()):
        shutil.copytree(hm.get_nam_dir(), os.path.join(backup_root, "NAM"))
    if os.path.exists(hm.get_blocks_v1_dir()):
        shutil.copytree(hm.get_blocks_v1_dir(), os.path.join(backup_root, "Blocks_ANXIETY_OD"))
    if os.path.exists(hm.get_blocks_v2_dir()):
        shutil.copytree(hm.get_blocks_v2_dir(), os.path.join(backup_root, "Blocks_ANXIETY_OD_V2"))
    print(f"[OK] Backup created successfully at: {backup_root}")

def main():
    parser = argparse.ArgumentParser(description="HeadRush MX5 NAM & IR Manager")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")
    
    # list
    subparsers.add_parser("list", help="List all occupied and free slots on MX5")
    
    # install
    p_inst = subparsers.add_parser("install", help="Install a NAM model to MX5")
    p_inst.add_argument("path", help="Relative or absolute path to .nam file")
    p_inst.add_argument("--slot", type=int, default=None, help="Specific slot number (0-100)")
    p_inst.add_argument("--name", type=str, default=None, help="Custom display name for the preset")
    p_inst.add_argument("--tone", type=int, default=50, help="Input Trim (0-100, default 50)")
    p_inst.add_argument("--level", type=int, default=70, help="Output Trim (0-100, default 70)")
    
    # search
    p_search = subparsers.add_parser("search", help="Search 97k library for models")
    p_search.add_argument("query", help="Search keyword (e.g. 5150, Bogner, Klon)")
    p_search.add_argument("--arch", choices=["all", "1", "2"], default="all", help="Filter by architecture: 1 (v1) or 2 (A2)")
    
    # irs
    subparsers.add_parser("irs", help="List all IR folders and files on MX5")
    
    # backup
    subparsers.add_parser("backup", help="Backup existing NAM models and presets from MX5")
    
    args = parser.parse_args()
    if args.command == "list" or not args.command:
        cmd_list(args)
    elif args.command == "install":
        cmd_install(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "irs":
        cmd_irs(args)
    elif args.command == "backup":
        cmd_backup(args)

if __name__ == "__main__":
    main()
