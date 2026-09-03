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

def cmd_list(args):
    print("\n=======================================================")
    print(" 🎸 HEADRUSH MX5 · INSTALLED NAM MODELS & BLOCK PRESETS")
    print("=======================================================")
    if not hm.is_headrush_connected():
        print("[!] HeadRush MX5 drive not detected.")
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
        print("[!] HeadRush MX5 drive not detected.")
        return
        
    nam_path = os.path.abspath(args.path)
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
    print(f"  Block Paths: {', '.join(res.get('block_paths', []))}")

def cmd_search(args):
    q = args.query
    print(f"\nSearching TONE3000 Cloud for '{q}'...")
    try:
        res = hm.cloud_search_tones(query=q)
        tones = res.get("tones", [])
        print(f"\nFound {len(tones)} results on TONE3000 Cloud:")
        print("-" * 90)
        for t in tones:
            tid = t.get("id")
            title = t.get("title") or t.get("name") or "Untitled"
            gear = t.get("gear", "amp").upper()
            author = (t.get("user") or {}).get("username") or "Community"
            models_cnt = t.get("models_count", 1)
            print(f"[{gear:<6}] ID: {tid:<6} | {title:<35} | Author: {author:<15} | Models: {models_cnt}")
    except Exception as e:
        print(f"[!] Cloud search error: {e}")

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

def cmd_batch(args):
    if not hm.is_headrush_connected():
        print("[!] HeadRush MX5 not detected.")
        return
    paths = args.paths
    smart = not args.no_smart
    print(f"Importing batch of models from {len(paths)} target(s)...")
    res = hm.import_local_models_batch(paths, smart_rename=smart)
    print(f"[OK] Installed {res['count']} models to HeadRush MX5.")
    if res['skipped']:
        print(f"Skipped {len(res['skipped'])} files:")
        for sk in res['skipped']:
            print(f"  - {sk['file']}: {sk['reason']}")

def cmd_organize(args):
    if not hm.is_headrush_connected():
        print("[!] HeadRush MX5 not detected.")
        return
    print("Running HeadRush Organize Wizard...")
    cleaned = hm.clean_orphaned_blocks()
    if cleaned:
        print(f"[OK] Cleaned {len(cleaned)} orphaned block presets.")
    sort_by = "alpha" if args.alpha else "current"
    res = hm.defrag_and_reorder_slots(sort_by=sort_by, make_safety_backup=True)
    print(f"[OK] Defragmented and reordered {res['count']} slots. Backup saved.")

def cmd_cheatsheet(args):
    fmt = args.format
    out = args.output
    sheet = hm.generate_stage_cheat_sheet(fmt)
    if out:
        with open(out, 'w', encoding='utf-8') as f:
            f.write(sheet)
        print(f"[OK] Stage cheat sheet saved to: {out}")
    else:
        print(sheet)

def cmd_duplicates(args):
    print("Checking for duplicate models on HeadRush MX5...")
    dupes = hm.detect_duplicate_models()
    print(f"Total duplicates detected: {dupes['total_duplicates']}")
    if dupes['hash_duplicates']:
        print("\nIdentical Content Duplicates (SHA-256):")
        for h, items in dupes['hash_duplicates'].items():
            print(f"  Hash {h[:12]}... -> {len(items)} slots:")
            for it in items:
                print(f"    - Slot {it['slot']:03d}: {it['preset_name']} ({it['file']})")
    if dupes['name_duplicates']:
        print("\nIdentical Preset Names:")
        for name, slots in dupes['name_duplicates'].items():
            print(f"  '{name}' -> Slots: {', '.join(f'{s:03d}' for s in slots)}")

def cmd_inspect(args):
    path = args.path
    if not os.path.exists(path):
        print(f"[!] File not found: {path}")
        return
    meta = hm.inspect_nam_file(path)
    print(f"\n=======================================================")
    print(f" 🔍 NAM MODEL INSPECTOR: {meta['filename']}")
    print(f"=======================================================")
    print(f"Valid NAM Model:  {meta['valid']}")
    print(f"Architecture:     {meta['architecture']}")
    print(f"Sample Rate:      {meta['sample_rate']} Hz")
    print(f"File Size:        {meta['size_kb']} KB")
    print(f"Author / Creator: {meta['author']}")
    print(f"Training Loss:    {meta['training_loss']}")
    print(f"Date:             {meta['date']}")
    if meta['description']:
        print(f"Description:      {meta['description']}")

def cmd_health(args):
    print("Diagnosing HeadRush MX5 health & integrity...")
    h = hm.perform_health_check()
    print(f"\n=======================================================")
    print(f" ❤️ SYSTEM HEALTH SCORE: {h['score']}% ({'HEALTHY' if h['healthy'] else 'ISSUES FOUND'})")
    print(f"=======================================================")
    print(f"Summary:        {h['summary']}")
    print(f"Total Models:   {h['total_models']}")
    if h['issues']:
        print("\nCritical Issues:")
        for iss in h['issues']:
            print(f"  ❌ {iss}")
    if h['warnings']:
        print("\nWarnings:")
        for w in h['warnings']:
            print(f"  ⚠️ {w}")
    if not h['issues'] and not h['warnings']:
        print("\n✓ Perfect condition! All blocks and models are 100% in sync.")

def cmd_storage(args):
    st = hm.get_storage_status()
    print(f"\n=======================================================")
    print(f" 💾 STORAGE & CAPACITY STATUS · DRIVE {st['drive']}")
    print(f"=======================================================")
    print(f"Connected:      {st['connected']}")
    print(f"Slots Used:     {st['slots_used']} / {st['slots_total']} ({st['slots_percent']}%)")
    print(f"Slots Free:     {st['slots_free']}")
    print(f"Disk Total:     {st['disk']['total_gb']} GB")
    print(f"Disk Free:      {st['disk']['free_gb']} GB (Used: {st['disk']['percent_used']}%)")

def cmd_eject(args):
    res = hm.safe_eject_headrush()
    print(f"\n⏏️ {res['message']}")
    print("It is now safe to disconnect your HeadRush MX5 USB cable.")

def cmd_setlist(args):
    sub = args.setlist_action
    if sub == "list" or not sub:
        lists = hm.list_setlists()
        print(f"\nSaved Setlists ({len(lists)} found):")
        for s in lists:
            print(f"  🗂️  {s['name']:<24} ({s['total_slots']} slots) - Created: {s['created_at'][:10]}")
    elif sub == "save":
        s_dir = hm.save_setlist(args.name)
        print(f"[OK] Setlist '{args.name}' saved to: {s_dir}")
    elif sub == "load":
        res = hm.load_setlist(args.name)
        print(f"[OK] Setlist '{args.name}' loaded to HeadRush MX5 ({res['restored_models']} models).")
    elif sub == "export":
        hm.export_setlist_zip(args.name, args.target)
        print(f"[OK] Setlist '{args.name}' exported to: {args.target}")
    elif sub == "import":
        dest = hm.import_setlist_zip(args.source)
        print(f"[OK] Setlist imported successfully from: {args.source}")

def cmd_cloud(args):
    action = args.cloud_action
    if action == "search":
        print(f"\n🔍 Searching TONE3000 Cloud for '{args.query}'...")
        res = hm.cloud_search_tones(query=args.query, gear=args.gear, page=args.page)
        tones = res.get("tones", [])
        print(f"Found {res.get('total', len(tones))} results (Page {res.get('page', 1)}/{res.get('total_pages', 1)}):\n")
        print(f"{'Tone ID':<10} | {'Title':<30} | {'Gear':<8} | {'Models':<6} | {'Author':<15}")
        print("-" * 75)
        for t in tones:
            author = (t.get("user") or {}).get("username", "Unknown")
            print(f"{t.get('id', ''):<10} | {t.get('title', '')[:30]:<30} | {t.get('gear', ''):<8} | {t.get('models_count', 0):<6} | {author[:15]:<15}")
    elif action == "trending":
        print("\n🔥 Top Trending Tones on TONE3000 Cloud:\n")
        tones = hm.cloud_get_trending(gear=args.gear)
        print(f"{'Tone ID':<10} | {'Title':<30} | {'Gear':<8} | {'Likes':<6} | {'Downloads':<10}")
        print("-" * 75)
        for t in tones:
            print(f"{t.get('id', ''):<10} | {t.get('title', '')[:30]:<30} | {t.get('gear', ''):<8} | {t.get('favorites_count', 0):<6} | {t.get('downloads_count', 0):<10}")
    elif action == "latest":
        print("\n✨ Latest Community Tones on TONE3000 Cloud:\n")
        tones = hm.cloud_get_latest(gear=args.gear)
        print(f"{'Tone ID':<10} | {'Title':<30} | {'Gear':<8} | {'Author':<15}")
        print("-" * 70)
        for t in tones:
            author = (t.get("user") or {}).get("username", "Unknown")
            print(f"{t.get('id', ''):<10} | {t.get('title', '')[:30]:<30} | {t.get('gear', ''):<8} | {author[:15]:<15}")
    elif action == "models":
        tone_id = args.tone_id
        if tone_id is None and args.query and args.query.isdigit():
            tone_id = int(args.query)
        if tone_id is None:
            print("[ERROR] Please provide a valid Tone ID (e.g. 'headrush_cli cloud models 2599')")
            return
        print(f"\n📦 Fetching models for Tone ID {tone_id}...")
        models = hm.cloud_get_tone_models(tone_id)
        print(f"Total captures available: {len(models)}\n")
        print(f"{'Model ID':<10} | {'Capture Name':<35} | {'Size/Arch':<15}")
        print("-" * 65)
        for m in models:
            print(f"{m.get('id', ''):<10} | {m.get('name', '')[:35]:<35} | {m.get('size', 'Standard'):<15}")
    elif action == "install":
        tone_id = args.tone_id
        if tone_id is None and args.query and args.query.isdigit():
            tone_id = int(args.query)
        if tone_id is None:
            print("[ERROR] Please provide a valid Tone ID (e.g. 'headrush_cli cloud install 2599')")
            return
        print(f"\n⚡ Installing Model from TONE3000 Cloud (Tone ID: {tone_id})...")
        models = hm.cloud_get_tone_models(tone_id)
        if not models:
            print(f"[ERROR] No models found for Tone ID {tone_id}")
            return
        target = None
        if getattr(args, "model_name", None):
            for m in models:
                if args.model_name.lower() in m.get("name", "").lower():
                    target = m
                    break
        if not target:
            target = models[0]
            
        print(f"Downloading '{target.get('name')}'...")
        res = hm.cloud_download_and_install(
            model_obj=target,
            slot=args.slot,
            custom_name=args.name or target.get("name"),
            tone=args.tone,
            level=args.level
        )
        print(f"\n[OK] Successfully installed cloud model to slot {res['slot']:03d}!")
        print(f"  Preset Name: {res['preset_name']}")
        print(f"  Tone File:   {res['nam_file']}")
        print(f"  Arch:        {res.get('cloud_info', {}).get('architecture', 'WaveNet')}")


def main():
    parser = argparse.ArgumentParser(description="HeadRush MX5 NAM & IR Manager Pro")
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
    
    # batch
    p_batch = subparsers.add_parser("batch", help="Batch install NAM models from folder or files")
    p_batch.add_argument("paths", nargs="+", help="Paths to folders or .nam files")
    p_batch.add_argument("--no-smart", action="store_true", help="Disable automatic LCD name shortening")

    # organize
    p_org = subparsers.add_parser("organize", help="Defragment and reorder slots")
    p_org.add_argument("--alpha", action="store_true", help="Sort alphabetically instead of current order")

    # cheatsheet
    p_sheet = subparsers.add_parser("cheatsheet", help="Generate stage cheat sheet")
    p_sheet.add_argument("--format", choices=["txt", "md", "html"], default="txt", help="Output format")
    p_sheet.add_argument("--output", "-o", default=None, help="Output file path")

    # duplicates
    subparsers.add_parser("duplicates", help="Check for duplicate models and names")

    # inspect
    p_insp = subparsers.add_parser("inspect", help="Inspect metadata of a .nam file")
    p_insp.add_argument("path", help="Path to .nam file")

    # health
    subparsers.add_parser("health", help="Check system health and block integrity")

    # storage
    subparsers.add_parser("storage", help="Check storage and slot usage")

    # eject
    subparsers.add_parser("eject", help="Flush writes and safely eject USB")

    # setlist
    p_setlist = subparsers.add_parser("setlist", help="Manage setlists and profiles")
    p_setlist.add_argument("setlist_action", choices=["list", "save", "load", "export", "import"], nargs="?", default="list")
    p_setlist.add_argument("--name", default="Default_Setlist", help="Setlist name")
    p_setlist.add_argument("--target", default="Setlist.hrpack", help="Target path for export")
    p_setlist.add_argument("--source", default=None, help="Source zip path for import")

    # search
    p_search = subparsers.add_parser("search", help="Search 97k library for models")
    p_search.add_argument("query", help="Search keyword (e.g. 5150, Bogner, Klon)")
    p_search.add_argument("--arch", choices=["all", "1", "2"], default="all", help="Filter by architecture: 1 (v1) or 2 (A2)")
    
    # irs
    subparsers.add_parser("irs", help="List all IR folders and files on MX5")
    
    # backup
    subparsers.add_parser("backup", help="Backup existing NAM models and presets from MX5")

    # cloud (TONE3000)
    p_cloud = subparsers.add_parser("cloud", help="Browse, search, and install community tones from TONE3000 Cloud")
    p_cloud.add_argument("cloud_action", choices=["search", "trending", "latest", "models", "install"], help="Action to perform")
    p_cloud.add_argument("query", nargs="?", default="", help="Search query (e.g. 'Mesa', 'Klon', 'Friedman')")
    p_cloud.add_argument("--gear", choices=["amp", "pedal", "cab", "full_rig"], default=None, help="Filter by gear type")
    p_cloud.add_argument("--page", type=int, default=1, help="Results page number")
    p_cloud.add_argument("--tone-id", type=int, default=None, help="TONE3000 Tone ID")
    p_cloud.add_argument("--model-name", type=str, default=None, help="Name filter for model inside tone")
    p_cloud.add_argument("--slot", type=int, default=None, help="Destination HeadRush slot (0-100)")
    p_cloud.add_argument("--name", type=str, default=None, help="Custom preset name")
    p_cloud.add_argument("--tone", type=int, default=50, help="Input Trim (0-100)")
    p_cloud.add_argument("--level", type=int, default=70, help="Output Trim (0-100)")
    
    args = parser.parse_args()
    if args.command == "list" or not args.command:
        cmd_list(args)
    elif args.command == "install":
        cmd_install(args)
    elif args.command == "batch":
        cmd_batch(args)
    elif args.command == "organize":
        cmd_organize(args)
    elif args.command == "cheatsheet":
        cmd_cheatsheet(args)
    elif args.command == "duplicates":
        cmd_duplicates(args)
    elif args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "health":
        cmd_health(args)
    elif args.command == "storage":
        cmd_storage(args)
    elif args.command == "eject":
        cmd_eject(args)
    elif args.command == "setlist":
        cmd_setlist(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "irs":
        cmd_irs(args)
    elif args.command == "backup":
        cmd_backup(args)
    elif args.command == "cloud":
        cmd_cloud(args)

if __name__ == "__main__":
    main()
