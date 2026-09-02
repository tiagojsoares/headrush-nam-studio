import os
import sys
import json
import uuid
import re
import shutil
import sqlite3
import threading
from datetime import datetime
import string
import ctypes

try:
    import customtkinter as ctk
    from tkinter import messagebox, filedialog
except ImportError:
    print("CustomTkinter or Tkinter not installed.")
    sys.exit(1)

# App Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

DB_PATH = "c:/VM/TONE3000_NAM_Library/tone3000.db"
LIBRARY_DIR = "c:/VM/TONE3000_NAM_Library"

def get_available_drives():
    """Returns a list of drive letters currently mounted on Windows."""
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(f"{letter}:")
        bitmask >>= 1
    return drives

def detect_headrush_drive():
    """Auto-detect which drive letter is the HeadRush MX5."""
    # Check E: first
    if os.path.exists("E:/NAM") and os.path.exists("E:/Blocks"):
        return "E:"
    # Check all other mounted drives
    for d in get_available_drives():
        if os.path.exists(os.path.join(d, "NAM")) and os.path.exists(os.path.join(d, "Blocks")):
            return d
    return None

class HeadRushBackend:
    def __init__(self, drive="E:"):
        self.drive = drive
        
    def set_drive(self, drive):
        self.drive = drive
        
    @property
    def nam_dir(self):
        return os.path.join(self.drive, "NAM")
        
    @property
    def blocks_v1_dir(self):
        return os.path.join(self.drive, "Blocks", "ANXIETY OD")
        
    @property
    def blocks_v2_dir(self):
        return os.path.join(self.drive, "Blocks", "ANXIETY OD V2")
        
    @property
    def ir_dir(self):
        return os.path.join(self.drive, "Impulse Responses")
        
    @property
    def ir_blocks_dir(self):
        return os.path.join(self.drive, "Blocks", "IR")
        
    def is_connected(self):
        if not self.drive:
            return False
        # Consider connected if the drive exists and contains any known HeadRush folder
        return os.path.exists(self.drive) and (
            os.path.exists(os.path.join(self.drive, "Blocks")) or 
            os.path.exists(os.path.join(self.drive, "Rigs")) or 
            os.path.exists(os.path.join(self.drive, "NAM"))
        )
        
    def get_free_space_gb(self):
        if not self.is_connected():
            return 0.0
        try:
            total, used, free = shutil.disk_usage(self.drive)
            return free / (1024 ** 3)
        except:
            return 0.0

    def get_installed_slots(self):
        if not self.is_connected():
            return {}
            
        slots = {}
        # 1. Scan NAM files
        if os.path.exists(self.nam_dir):
            try:
                for f in os.listdir(self.nam_dir):
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
            except:
                pass
                
        # Helper to read blocks
        def read_blocks(b_dir, v_key):
            if not os.path.exists(b_dir): return
            try:
                for f in os.listdir(b_dir):
                    if f.lower().endswith('.block'):
                        m = re.match(r'^(\d{3})\s*-\s*(.*)\.block$', f, re.IGNORECASE)
                        if m:
                            slot_num = int(m.group(1))
                            if slot_num not in slots:
                                slots[slot_num] = {
                                    'slot': slot_num, 'slot_str': f"{slot_num:03d}",
                                    'nam_file': None, 'nam_name': None,
                                    'block_file_v1': None, 'block_file_v2': None,
                                    'preset_name': m.group(2), 'tone': 50, 'level': 70
                                }
                            slots[slot_num][v_key] = f
                            if not slots[slot_num]['preset_name']:
                                slots[slot_num]['preset_name'] = m.group(2)
                                
                            try:
                                with open(os.path.join(b_dir, f), 'r', encoding='utf-8') as bfp:
                                    d = json.load(bfp)
                                    content = json.loads(d['content'])
                                    pedal_type = 'Anxiety OD' if v_key == 'block_file_v1' else 'Anxiety OD V2'
                                    pedal = content['data'][pedal_type]['children']
                                    slots[slot_num]['drive'] = pedal['Drive']['value']
                                    slots[slot_num]['tone'] = pedal['Tone']['value']
                                    slots[slot_num]['level'] = pedal['Level']['value']
                            except:
                                pass
            except:
                pass

        read_blocks(self.blocks_v1_dir, 'block_file_v1')
        read_blocks(self.blocks_v2_dir, 'block_file_v2')
        return slots

    def get_next_free_slot(self):
        slots = self.get_installed_slots()
        for s in range(101):
            if s not in slots or not slots[s]['nam_file']:
                return s
        return None

    def sanitize_preset_name(self, text, max_len=26):
        clean = re.sub(r'[^\w\s\-\+\.]', '', text)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean[:max_len].strip()

    def create_block_preset(self, slot_num, preset_name, tone=50, level=70):
        # Create BOTH V1 and V2 blocks so the user's mod works no matter what
        filename = f"{slot_num:03d} - {preset_name}.block"
        
        # V1
        os.makedirs(self.blocks_v1_dir, exist_ok=True)
        path_v1 = os.path.join(self.blocks_v1_dir, filename)
        inner_v1 = {
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
        obj_v1 = {
            "content": json.dumps(inner_v1, separators=(',', ':')),
            "id": str(uuid.uuid4()),
            "readonly": False,
            "type": "ANXIETY OD"
        }
        with open(path_v1, 'w', encoding='utf-8') as f:
            json.dump(obj_v1, f, separators=(',', ':'))
            
        # V2
        os.makedirs(self.blocks_v2_dir, exist_ok=True)
        path_v2 = os.path.join(self.blocks_v2_dir, filename)
        inner_v2 = {
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
        obj_v2 = {
            "content": json.dumps(inner_v2, separators=(',', ':')),
            "id": str(uuid.uuid4()),
            "readonly": False,
            "type": "ANXIETY OD V2"
        }
        with open(path_v2, 'w', encoding='utf-8') as f:
            json.dump(obj_v2, f, separators=(',', ':'))
            
        return path_v1

    def install_model(self, src_path, preset_name=None, slot=None, tone=50, level=70):
        if not self.is_connected():
            raise Exception("HeadRush MX5 não está conectada na unidade atual.")
            
        if slot is None:
            slot = self.get_next_free_slot()
            if slot is None:
                raise Exception("Limite atingido! Todos os 101 slots estão ocupados.")
                
        base_name = preset_name or os.path.splitext(os.path.basename(src_path))[0]
        base_name = re.sub(r'^\d{3}\s*-\s*', '', base_name)
        
        # 1. Copy NAM
        os.makedirs(self.nam_dir, exist_ok=True)
        clean_nam = re.sub(r'[\/*?:"<>|]', '_', base_name)
        nam_filename = f"{slot:03d} - {clean_nam}.nam"
        dest_nam = os.path.join(self.nam_dir, nam_filename)
        shutil.copy2(src_path, dest_nam)
        
        # 2. Create Block Presets
        short_name = self.sanitize_preset_name(base_name, 24)
        dest_block = self.create_block_preset(slot, short_name, tone=tone, level=level)
        
        return {
            "slot": slot,
            "nam_file": nam_filename,
            "preset_name": short_name,
            "block_path": dest_block
        }

    def delete_slot(self, slot_num):
        slots = self.get_installed_slots()
        if slot_num in slots:
            info = slots[slot_num]
            if info['nam_file']:
                npath = os.path.join(self.nam_dir, info['nam_file'])
                if os.path.exists(npath):
                    os.remove(npath)
            if info.get('block_file_v1'):
                bpath = os.path.join(self.blocks_v1_dir, info['block_file_v1'])
                if os.path.exists(bpath):
                    os.remove(bpath)
            if info.get('block_file_v2'):
                bpath = os.path.join(self.blocks_v2_dir, info['block_file_v2'])
                if os.path.exists(bpath):
                    os.remove(bpath)
            return True
        return False

    def update_slot_trims(self, slot_num, preset_name, tone, level):
        slots = self.get_installed_slots()
        if slot_num in slots:
            info = slots[slot_num]
            new_preset_name = self.sanitize_preset_name(preset_name, 24)
            # Delete old blocks
            if info.get('block_file_v1'):
                old_path = os.path.join(self.blocks_v1_dir, info['block_file_v1'])
                if os.path.exists(old_path): os.remove(old_path)
            if info.get('block_file_v2'):
                old_path = os.path.join(self.blocks_v2_dir, info['block_file_v2'])
                if os.path.exists(old_path): os.remove(old_path)
            # Recreate both blocks
            self.create_block_preset(slot_num, new_preset_name, tone=tone, level=level)
            return True
        return False

    def get_irs(self):
        if not os.path.exists(self.ir_dir):
            return []
        irs = []
        for root, dirs, files in os.walk(self.ir_dir):
            for f in files:
                if f.lower().endswith(('.wav', '.aif', '.aiff')):
                    rel = os.path.relpath(root, self.ir_dir)
                    folder = "[USER]" if rel == '.' else rel.split(os.sep)[0]
                    name_no_ext = os.path.splitext(f)[0]
                    irs.append({
                        "folder": folder,
                        "filename": f,
                        "name": name_no_ext,
                        "path": os.path.join(root, f)
                    })
        return irs

    def create_ir_block(self, preset_name, ir_folder, ir_name, gain=-10.0, hi_cut=10000, lo_cut=50):
        os.makedirs(self.ir_blocks_dir, exist_ok=True)
        filename = f"{self.sanitize_preset_name(preset_name, 24)}.block"
        path = os.path.join(self.ir_blocks_dir, filename)
        
        ir_str = f"[directory]({ir_folder})[name]({ir_name})"
        inner = {
            "data": {
                "IR": {
                    "childorder": ["DoubleStates", "IR", "Gain", "HiCut", "LoCut", "Mix"],
                    "children": {
                        "DoubleStates": {"state": False, "type": 3},
                        "Gain": {"type": 0, "value": float(gain)},
                        "HiCut": {"type": 0, "value": int(hi_cut)},
                        "IR": {"string": ir_str, "type": 8},
                        "LoCut": {"type": 0, "value": int(lo_cut)},
                        "Mix": {"type": 0, "value": 100}
                    }
                }
            },
            "info": {"version": "1.0.9"}
        }
        obj = {
            "content": json.dumps(inner, separators=(',', ':')),
            "id": str(uuid.uuid4()),
            "readonly": False,
            "type": "IR"
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(obj, f, separators=(',', ':'))
        return path

    def backup(self):
        if not self.is_connected():
            raise Exception("Pedaleira não conectada.")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"c:/VM/HeadRush_Backup_{ts}"
        os.makedirs(backup_dir, exist_ok=True)
        if os.path.exists(self.nam_dir):
            shutil.copytree(self.nam_dir, os.path.join(backup_dir, "NAM"))
        if os.path.exists(self.blocks_v1_dir):
            shutil.copytree(self.blocks_v1_dir, os.path.join(backup_dir, "Blocks_ANXIETY_OD"))
        if os.path.exists(self.blocks_v2_dir):
            shutil.copytree(self.blocks_v2_dir, os.path.join(backup_dir, "Blocks_ANXIETY_OD_V2"))
        return backup_dir

class HeadRushApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("HeadRush MX5 · NAM Studio Pro")
        self.geometry("1100x720")
        self.minsize(950, 600)
        
        # Detect drive
        detected_drive = detect_headrush_drive() or "E:"
        self.backend = HeadRushBackend(detected_drive)
        
        # Build UI
        self.build_header()
        self.build_tabs()
        
        # Start initial load
        self.refresh_connection()
        self.refresh_installed_slots()

    def build_header(self):
        self.header_frame = ctk.CTkFrame(self, height=75, corner_radius=0, fg_color="#18181b")
        self.header_frame.pack(fill="x", side="top")
        
        # Logo & Title
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)
        
        title_label = ctk.CTkLabel(
            title_box, 
            text="HEADRUSH MX5 · NAM STUDIO", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#f4f4f5"
        )
        title_label.pack(anchor="w")
        
        sub_label = ctk.CTkLabel(
            title_box, 
            text="Gerenciador Inteligente de Timbres NAM, Presets e IRs · 97k Library", 
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa"
        )
        sub_label.pack(anchor="w")
        
        # Right controls: Drive status & Backup
        ctrl_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        ctrl_box.pack(side="right", padx=20, pady=12)
        
        self.status_badge = ctk.CTkLabel(
            ctrl_box,
            text="Verificando...",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#27272a",
            corner_radius=6,
            padx=12,
            pady=6
        )
        self.status_badge.pack(side="left", padx=8)
        
        # Drive selector dropdown
        drives = get_available_drives()
        self.drive_menu = ctk.CTkOptionMenu(
            ctrl_box,
            values=drives if drives else ["E:"],
            width=70,
            command=self.on_drive_changed
        )
        if self.backend.drive in drives:
            self.drive_menu.set(self.backend.drive)
        self.drive_menu.pack(side="left", padx=6)
        
        btn_refresh = ctk.CTkButton(
            ctrl_box,
            text="🔄",
            width=36,
            fg_color="#3f3f46",
            hover_color="#52525b",
            command=self.refresh_connection
        )
        btn_refresh.pack(side="left", padx=4)
        
        btn_backup = ctk.CTkButton(
            ctrl_box,
            text="💾 Fazer Backup",
            width=110,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.trigger_backup
        )
        btn_backup.pack(side="left", padx=6)

    def build_tabs(self):
        self.tabview = ctk.CTkTabview(self, corner_radius=10, fg_color="#121214")
        self.tabview.pack(fill="both", expand=True, padx=16, pady=12)
        
        self.tab_installed = self.tabview.add("  🎸 Minha Pedaleira (Slots 000-100)  ")
        self.tab_catalog = self.tabview.add("  🔍 Catálogo TONE3000 (97k Timbres)  ")
        self.tab_irs = self.tabview.add("  🔊 Impulse Responses (IRs)  ")
        self.tab_help = self.tabview.add("  ℹ️ Instruções e Ajuda  ")
        
        self.setup_installed_tab()
        self.setup_catalog_tab()
        self.setup_irs_tab()
        self.setup_help_tab()

    # ====================================================================
    # TAB 1: INSTALLED SLOTS
    # ====================================================================
    def setup_installed_tab(self):
        top_bar = ctk.CTkFrame(self.tab_installed, fg_color="#1e1e24", corner_radius=8)
        top_bar.pack(fill="x", padx=10, pady=8)
        
        self.lbl_slot_summary = ctk.CTkLabel(
            top_bar,
            text="Carregando slots...",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_slot_summary.pack(side="left", padx=16, pady=10)
        
        self.ent_filter_installed = ctk.CTkEntry(
            top_bar,
            placeholder_text="Filtrar por nome ou número...",
            width=260
        )
        self.ent_filter_installed.pack(side="right", padx=16, pady=10)
        self.ent_filter_installed.bind("<KeyRelease>", lambda e: self.filter_installed_slots())
        
        # Scrollable container for slots
        self.slots_scroll = ctk.CTkScrollableFrame(self.tab_installed, fg_color="transparent")
        self.slots_scroll.pack(fill="both", expand=True, padx=6, pady=6)

    def refresh_installed_slots(self):
        for widget in self.slots_scroll.winfo_children():
            widget.destroy()
            
        slots = self.backend.get_installed_slots()
        occupied_count = len(slots)
        next_free = self.backend.get_next_free_slot()
        next_free_str = f"{next_free:03d}" if next_free is not None else "Cheio"
        
        self.lbl_slot_summary.configure(
            text=f"📊 Slots Ocupados: {occupied_count} / 101  ·  Livres: {101 - occupied_count}  ·  Próximo Livre: {next_free_str}"
        )
        
        if not self.backend.is_connected():
            empty_lbl = ctk.CTkLabel(
                self.slots_scroll,
                text="Pedaleira não detectada.\nConecte o cabo USB da HeadRush MX5 e clique em 🔄 Atualizar.",
                font=ctk.CTkFont(size=15),
                text_color="#71717a"
            )
            empty_lbl.pack(pady=60)
            return

        filter_text = self.ent_filter_installed.get().strip().lower()
        
        for s in sorted(slots.keys()):
            info = slots[s]
            pname = info.get('preset_name') or "(Sem preset)"
            nfile = info.get('nam_file') or "(Sem arquivo .nam)"
            
            if filter_text and filter_text not in pname.lower() and filter_text not in str(s) and filter_text not in nfile.lower():
                continue
                
            self.create_slot_row(info)

    def create_slot_row(self, info):
        row = ctk.CTkFrame(self.slots_scroll, fg_color="#18181b", corner_radius=8)
        row.pack(fill="x", pady=4, padx=4)
        
        # Slot badge
        slot_lbl = ctk.CTkLabel(
            row,
            text=f"SLOT {info['slot']:03d}",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284c7",
            text_color="#ffffff",
            corner_radius=6,
            width=75,
            height=28
        )
        slot_lbl.pack(side="left", padx=10, pady=8)
        
        # Drive knob value
        drive_lbl = ctk.CTkLabel(
            row,
            text=f"Drive: {info.get('drive', info['slot'])}%",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f59e0b",
            width=80
        )
        drive_lbl.pack(side="left", padx=5)
        
        # Preset Name & File
        center_box = ctk.CTkFrame(row, fg_color="transparent")
        center_box.pack(side="left", fill="x", expand=True, padx=10)
        
        preset_title = ctk.CTkLabel(
            center_box,
            text=info.get('preset_name') or "(Sem preset .block)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff",
            anchor="w"
        )
        preset_title.pack(anchor="w")
        
        file_desc = ctk.CTkLabel(
            center_box,
            text=f"Arquivo: {info.get('nam_file') or 'N/A'}",
            font=ctk.CTkFont(size=11),
            text_color="#71717a",
            anchor="w"
        )
        file_desc.pack(anchor="w")
        
        # Trims display
        trims_lbl = ctk.CTkLabel(
            row,
            text=f"Tone: {info.get('tone', 50)} | Vol: {info.get('level', 70)}",
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa",
            width=130
        )
        trims_lbl.pack(side="left", padx=10)
        
        # Actions
        btn_edit = ctk.CTkButton(
            row,
            text="✏️ Trims",
            width=65,
            height=28,
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=lambda s=info['slot']: self.open_edit_dialog(s)
        )
        btn_edit.pack(side="right", padx=6)
        
        btn_del = ctk.CTkButton(
            row,
            text="🗑️",
            width=36,
            height=28,
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            command=lambda s=info['slot']: self.confirm_delete_slot(s)
        )
        btn_del.pack(side="right", padx=6)

    def filter_installed_slots(self):
        self.refresh_installed_slots()

    def open_edit_dialog(self, slot_num):
        slots = self.backend.get_installed_slots()
        if slot_num not in slots:
            return
        info = slots[slot_num]
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Ajustar Slot {slot_num:03d}")
        dialog.geometry("400x320")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(
            dialog,
            text=f"Calibrar Timbre - Slot {slot_num:03d}",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=12)
        
        # Name
        name_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        name_frame.pack(fill="x", padx=25, pady=6)
        ctk.CTkLabel(name_frame, text="Nome no Visor:").pack(anchor="w")
        ent_name = ctk.CTkEntry(name_frame)
        ent_name.insert(0, info.get('preset_name') or "")
        ent_name.pack(fill="x", pady=4)
        
        # Tone Trim slider
        ctk.CTkLabel(dialog, text=f"Input Trim (Tone Knob):").pack(anchor="w", padx=25)
        slider_tone = ctk.CTkSlider(dialog, from_=0, to=100, number_of_steps=100)
        slider_tone.set(info.get('tone', 50))
        slider_tone.pack(fill="x", padx=25, pady=4)
        lbl_tone_val = ctk.CTkLabel(dialog, text=f"{int(slider_tone.get())}")
        lbl_tone_val.pack()
        slider_tone.configure(command=lambda v: lbl_tone_val.configure(text=str(int(v))))
        
        # Level Trim slider
        ctk.CTkLabel(dialog, text=f"Output Level (Volume):").pack(anchor="w", padx=25)
        slider_level = ctk.CTkSlider(dialog, from_=0, to=100, number_of_steps=100)
        slider_level.set(info.get('level', 70))
        slider_level.pack(fill="x", padx=25, pady=4)
        lbl_level_val = ctk.CTkLabel(dialog, text=f"{int(slider_level.get())}")
        lbl_level_val.pack()
        slider_level.configure(command=lambda v: lbl_level_val.configure(text=str(int(v))))
        
        def save():
            new_name = ent_name.get().strip() or info.get('preset_name')
            self.backend.update_slot_trims(slot_num, new_name, int(slider_tone.get()), int(slider_level.get()))
            dialog.destroy()
            self.refresh_installed_slots()
            
        btn_save = ctk.CTkButton(dialog, text="Salvar Ajustes", fg_color="#16a34a", hover_color="#15803d", command=save)
        btn_save.pack(pady=16)

    def confirm_delete_slot(self, slot_num):
        slots = self.backend.get_installed_slots()
        info = slots.get(slot_num, {})
        pname = info.get('preset_name') or f"Slot {slot_num:03d}"
        
        ans = messagebox.askyesno(
            "Confirmar Exclusão",
            f"Deseja realmente remover o timbre '{pname}' do Slot {slot_num:03d}?\n\nO slot ficará livre para outro timbre."
        )
        if ans:
            self.backend.delete_slot(slot_num)
            self.refresh_installed_slots()

    # ====================================================================
    # TAB 2: TONE3000 CATALOG
    # ====================================================================
    def setup_catalog_tab(self):
        # Search controls
        ctrl_frame = ctk.CTkFrame(self.tab_catalog, fg_color="#1e1e24", corner_radius=8)
        ctrl_frame.pack(fill="x", padx=10, pady=8)
        
        # Search input
        search_box = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        search_box.pack(fill="x", padx=12, pady=8)
        
        self.ent_search = ctk.CTkEntry(
            search_box,
            placeholder_text="Digite o amplificador, pedal ou timbre (ex: 5150, Dumble, Petrucci, Klon, SLO...)",
            height=38,
            font=ctk.CTkFont(size=13)
        )
        self.ent_search.pack(side="left", fill="x", expand=True, padx=6)
        self.ent_search.bind("<Return>", lambda e: self.perform_search())
        
        btn_search = ctk.CTkButton(
            search_box,
            text="🔍 Pesquisar",
            width=110,
            height=38,
            font=ctk.CTkFont(weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self.perform_search
        )
        btn_search.pack(side="right", padx=6)
        
        # Filters row
        filter_row = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        filter_row.pack(fill="x", padx=12, pady=4)
        
        ctk.CTkLabel(filter_row, text="Categoria:", text_color="#a1a1aa").pack(side="left", padx=4)
        self.filter_gear = ctk.CTkOptionMenu(
            filter_row,
            values=["Todos", "Amps", "Pedais", "Amp + Cab"],
            width=120,
            command=lambda v: self.perform_search()
        )
        self.filter_gear.pack(side="left", padx=6)
        
        ctk.CTkLabel(filter_row, text="Arquitetura:", text_color="#a1a1aa").pack(side="left", padx=8)
        self.filter_arch = ctk.CTkOptionMenu(
            filter_row,
            values=["A2 (Recomendado p/ MX5)", "Todos", "v1 Clássico"],
            width=180,
            command=lambda v: self.perform_search()
        )
        self.filter_arch.pack(side="left", padx=6)
        
        # Quick filter shortcuts
        chips_frame = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        chips_frame.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(chips_frame, text="Atalhos:", font=ctk.CTkFont(size=11), text_color="#71717a").pack(side="left", padx=4)
        
        shortcuts = ["5150", "Dumble", "Petrucci", "Andy Timmons", "1981 DRV", "Mesa Boogie", "Bogner", "Soldano", "Plexi"]
        for s in shortcuts:
            btn = ctk.CTkButton(
                chips_frame,
                text=s,
                height=24,
                width=65,
                font=ctk.CTkFont(size=11),
                fg_color="#27272a",
                hover_color="#3f3f46",
                command=lambda term=s: self.search_shortcut(term)
            )
            btn.pack(side="left", padx=3)
            
        # Search results scrollable area
        self.catalog_scroll = ctk.CTkScrollableFrame(self.tab_catalog, fg_color="transparent")
        self.catalog_scroll.pack(fill="both", expand=True, padx=6, pady=6)
        
        # Initial empty state
        self.show_search_placeholder()

    def show_search_placeholder(self):
        for widget in self.catalog_scroll.winfo_children():
            widget.destroy()
        lbl = ctk.CTkLabel(
            self.catalog_scroll,
            text="⚡ Pesquise qualquer timbre entre os 97.974 modelos locais\nou clique em um dos atalhos acima para explorar!",
            font=ctk.CTkFont(size=14),
            text_color="#71717a"
        )
        lbl.pack(pady=70)

    def search_shortcut(self, term):
        self.ent_search.delete(0, 'end')
        self.ent_search.insert(0, term)
        self.perform_search()

    def perform_search(self):
        q = self.ent_search.get().strip()
        if not q:
            self.show_search_placeholder()
            return
            
        for widget in self.catalog_scroll.winfo_children():
            widget.destroy()
            
        loading_lbl = ctk.CTkLabel(self.catalog_scroll, text="Buscando no acervo...", font=ctk.CTkFont(size=14))
        loading_lbl.pack(pady=40)
        
        gear_sel = self.filter_gear.get()
        arch_sel = self.filter_arch.get()
        
        # Run search query in a background thread to keep UI super responsive
        threading.Thread(target=self._run_search_thread, args=(q, gear_sel, arch_sel), daemon=True).start()

    def _run_search_thread(self, query, gear_sel, arch_sel):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        sql = '''
            SELECT m.id, m.name, t.title, COALESCE(u.username, u.display_name, 'Community'),
                   m.architecture_version, t.gear, m.local_path, t.description
            FROM models_fts fts
            JOIN models m ON fts.model_id = m.id
            JOIN tones t ON m.tone_id = t.id
            LEFT JOIN users u ON t.user_id = u.id
            WHERE models_fts MATCH ?
        '''
        params = [f'"{query}"*']
        
        if gear_sel == "Amps":
            sql += " AND t.gear = 'amp'"
        elif gear_sel == "Pedais":
            sql += " AND t.gear = 'pedal'"
        elif gear_sel == "Amp + Cab":
            sql += " AND t.gear = 'amp-cab'"
            
        if arch_sel == "A2 (Recomendado p/ MX5)":
            sql += " AND m.architecture_version = '2'"
        elif arch_sel == "v1 Clássico":
            sql += " AND m.architecture_version = '1'"
            
        sql += " LIMIT 50"
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        
        self.after(0, lambda: self._render_search_results(rows, query))

    def _render_search_results(self, rows, query):
        for widget in self.catalog_scroll.winfo_children():
            widget.destroy()
            
        if not rows:
            ctk.CTkLabel(
                self.catalog_scroll,
                text=f"Nenhum modelo encontrado para '{query}'. Tente outro termo.",
                font=ctk.CTkFont(size=14),
                text_color="#ef4444"
            ).pack(pady=40)
            return
            
        summary_lbl = ctk.CTkLabel(
            self.catalog_scroll,
            text=f"Mostrando {len(rows)} melhores resultados para '{query}':",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8",
            anchor="w"
        )
        summary_lbl.pack(fill="x", padx=8, pady=4)
        
        for r in rows:
            m_id, m_name, t_title, creator, a_ver, gear, rel_path, desc = r
            self.create_catalog_card(m_id, m_name, t_title, creator, a_ver, gear, rel_path)

    def create_catalog_card(self, m_id, m_name, t_title, creator, a_ver, gear, rel_path):
        card = ctk.CTkFrame(self.catalog_scroll, fg_color="#18181b", corner_radius=8)
        card.pack(fill="x", pady=4, padx=4)
        
        # Arch tag
        arch_color = "#16a34a" if a_ver == '2' else "#4b5563"
        arch_text = "A2 SLIM" if a_ver == '2' else "NAM v1"
        arch_badge = ctk.CTkLabel(
            card,
            text=arch_text,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=arch_color,
            text_color="#ffffff",
            corner_radius=4,
            width=60,
            height=22
        )
        arch_badge.pack(side="left", padx=10, pady=10)
        
        # Info Box
        info_box = ctk.CTkFrame(card, fg_color="transparent")
        info_box.pack(side="left", fill="x", expand=True, padx=8)
        
        title_lbl = ctk.CTkLabel(
            info_box,
            text=m_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff",
            anchor="w"
        )
        title_lbl.pack(anchor="w")
        
        gear_pt = {"amp": "Cabeçote", "pedal": "Pedal", "amp-cab": "Amp + Caixa", "outboard": "Outboard"}.get(gear, gear)
        desc_lbl = ctk.CTkLabel(
            info_box,
            text=f"Pacote: {t_title}  ·  Criador: {creator}  ·  Tipo: {gear_pt}",
            font=ctk.CTkFont(size=11),
            text_color="#a1a1aa",
            anchor="w"
        )
        desc_lbl.pack(anchor="w")
        
        # Install Button
        btn_send = ctk.CTkButton(
            card,
            text="⚡ Enviar p/ MX5",
            width=135,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=lambda p=rel_path, n=m_name: self.install_model_action(p, n)
        )
        btn_send.pack(side="right", padx=12, pady=10)

    def install_model_action(self, rel_path, model_name):
        if not self.backend.is_connected():
            messagebox.showerror("Erro", "A HeadRush MX5 não está conectada ou a unidade está incorreta.")
            return
            
        next_slot = self.backend.get_next_free_slot()
        if next_slot is None:
            messagebox.showwarning("Limite Atingido", "Todos os 101 slots estão ocupados! Exclua algum timbre antes.")
            return
            
        full_path = os.path.join(LIBRARY_DIR, rel_path.replace('/', os.sep))
        if not os.path.exists(full_path):
            messagebox.showerror("Arquivo não encontrado", f"Não foi possível localizar o arquivo no disco:\n{full_path}")
            return
            
        try:
            res = self.backend.install_model(full_path, preset_name=model_name, slot=next_slot)
            messagebox.showinfo(
                "Instalação Concluída! 🚀",
                f"Timbre instalado com sucesso no Slot {res['slot']:03d}!\n\n"
                f"⚠️ ATENÇÃO - PASSO OBRIGATÓRIO ⚠️\n"
                f"Como você adicionou novos arquivos, a HeadRush MX5 NÃO VAI reconhecê-los até você REINICIAR a pedaleira.\n\n"
                f"Passo a Passo:\n"
                f"1. Desconecte o cabo USB (ou saia do modo USB Transfer)\n"
                f"2. Desligue a HeadRush no botão e ligue novamente.\n"
                f"3. Vá no seu Rig, adicione o pedal Anxiety OD V2 e carregue o preset '{res['preset_name']}'!"
            )
            self.refresh_installed_slots()
        except Exception as e:
            messagebox.showerror("Erro ao Instalar", str(e))

    # ====================================================================
    # TAB 3: IMPULSE RESPONSES
    # ====================================================================
    def setup_irs_tab(self):
        top_bar = ctk.CTkFrame(self.tab_irs, fg_color="#1e1e24", corner_radius=8)
        top_bar.pack(fill="x", padx=10, pady=8)
        
        self.lbl_ir_count = ctk.CTkLabel(
            top_bar,
            text="Carregando IRs...",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_ir_count.pack(side="left", padx=16, pady=10)
        
        btn_refresh_irs = ctk.CTkButton(
            top_bar,
            text="🔄 Atualizar IRs",
            width=120,
            command=self.refresh_irs_list
        )
        btn_refresh_irs.pack(side="right", padx=16, pady=10)
        
        self.irs_scroll = ctk.CTkScrollableFrame(self.tab_irs, fg_color="transparent")
        self.irs_scroll.pack(fill="both", expand=True, padx=6, pady=6)
        
        self.refresh_irs_list()

    def refresh_irs_list(self):
        for widget in self.irs_scroll.winfo_children():
            widget.destroy()
            
        if not self.backend.is_connected():
            ctk.CTkLabel(
                self.irs_scroll,
                text="Pedaleira não conectada. Conecte no modo USB para gerenciar IRs.",
                font=ctk.CTkFont(size=14),
                text_color="#71717a"
            ).pack(pady=50)
            return
            
        irs = self.backend.get_irs()
        self.lbl_ir_count.configure(text=f"Total de Impulse Responses na HeadRush: {len(irs)} arquivos")
        
        # Group by folder
        folders = {}
        for ir in irs:
            folders.setdefault(ir['folder'], []).append(ir)
            
        for folder_name, folder_irs in sorted(folders.items()):
            grp_frame = ctk.CTkFrame(self.irs_scroll, fg_color="#18181b", corner_radius=8)
            grp_frame.pack(fill="x", pady=4, padx=4)
            
            ctk.CTkLabel(
                grp_frame,
                text=f"📁 {folder_name} ({len(folder_irs)} IRs)",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#f4f4f5"
            ).pack(side="left", padx=12, pady=10)
            
            btn_create_block = ctk.CTkButton(
                grp_frame,
                text="➕ Criar Preset de IR",
                width=140,
                height=28,
                fg_color="#27272a",
                hover_color="#3f3f46",
                command=lambda f=folder_name, ir_list=folder_irs: self.open_ir_block_creator(f, ir_list)
            )
            btn_create_block.pack(side="right", padx=12, pady=10)

    def open_ir_block_creator(self, folder_name, ir_list):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Criar Preset de IR")
        dialog.geometry("450x380")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(
            dialog,
            text=f"Criar Bloco de IR para {folder_name}",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=12)
        
        # Select specific file
        ctk.CTkLabel(dialog, text="Selecione o arquivo de IR:").pack(anchor="w", padx=25)
        names = [item['name'] for item in ir_list[:50]]
        menu_ir = ctk.CTkOptionMenu(dialog, values=names)
        menu_ir.pack(fill="x", padx=25, pady=4)
        
        # Preset name
        ctk.CTkLabel(dialog, text="Nome do Bloco de Preset:").pack(anchor="w", padx=25, pady=(8, 0))
        ent_preset = ctk.CTkEntry(dialog)
        ent_preset.insert(0, self.backend.sanitize_preset_name(names[0] if names else "CAB IR", 20))
        ent_preset.pack(fill="x", padx=25, pady=4)
        
        # Gain slider
        ctk.CTkLabel(dialog, text="Ganho de Saída (dB):").pack(anchor="w", padx=25, pady=(8, 0))
        slider_gain = ctk.CTkSlider(dialog, from_=-24, to=0, number_of_steps=48)
        slider_gain.set(-10)
        slider_gain.pack(fill="x", padx=25, pady=4)
        lbl_gain = ctk.CTkLabel(dialog, text="-10.0 dB")
        lbl_gain.pack()
        slider_gain.configure(command=lambda v: lbl_gain.configure(text=f"{v:.1f} dB"))
        
        def save():
            ir_name = menu_ir.get()
            pname = ent_preset.get().strip() or "CUSTOM IR"
            path = self.backend.create_ir_block(pname, folder_name, ir_name, gain=slider_gain.get())
            messagebox.showinfo("Sucesso", f"Preset de IR criado com sucesso em:\n{path}")
            dialog.destroy()
            
        btn_create = ctk.CTkButton(dialog, text="Criar Bloco de IR", fg_color="#16a34a", hover_color="#15803d", command=save)
        btn_create.pack(pady=20)

    # ====================================================================
    # TAB 4: HELP & INSTRUCTIONS
    # ====================================================================
    def setup_help_tab(self):
        frame = ctk.CTkScrollableFrame(self.tab_help, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        
        help_text = """
# 🎸 GUIA DE USO · HEADRUSH MX5 NAM MOD

### 🔌 1. Como Conectar e Desconectar a MX5
1. Conecte a pedaleira ao PC com o cabo USB.
2. Na tela da MX5, toque nos 3 pontinhos (Menu Global) -> **USB Transfer**.
3. A pedaleira aparecerá como uma unidade removível (geralmente `E:`).
4. Para desconectar com segurança: toque em **Sync / Eject** na tela da pedaleira antes de remover o cabo.
5. **IMPORTANTE**: Após transferir novos timbres, reinicie a pedaleira (desligue e ligue) para que o firmware leia os novos arquivos da pasta `/NAM`.

---

### 🎛️ 2. Como Tocar os Timbres na MX5
1. Em qualquer Rig, adicione o pedal **Anxiety OD V2**.
2. Toque no pedal e abra a lista de **Presets**.
3. Você verá todos os seus presets numerados exatamente com o slot (ex.: `028 - 1981 DRV MED GAIN`, `031 - DUMBLE SSS CLEAN EVM`).
4. Ao selecionar o preset:
   - O botão **DRIVE** irá exatamente para a posição do modelo NAM!
   - O botão **TONE** funciona como ajuste fino de ganho de entrada (**Input Trim**).
   - O botão **LEVEL** funciona como volume final (**Output Trim**).

---

### 🔊 3. Dica sobre Gabinetes e IRs
- **Modelos [A2] Cabeçote (Amps)**: Requerem um bloco de **IR** logo após o Anxiety OD V2. Use a aba "Impulse Responses" para criar blocos prontos!
- **Modelos [A2] Full Rig (Amp+Cab)**: Já possuem gabinete capturado no arquivo, não precisa de IR adicional.
- **Pedais de Overdrive/Distorção**: Devem ser posicionados antes do amplificador no seu rig.
"""
        lbl = ctk.CTkLabel(
            frame,
            text=help_text,
            justify="left",
            font=ctk.CTkFont(size=13),
            text_color="#d4d4d8"
        )
        lbl.pack(anchor="w", padx=10, pady=10)

    # ====================================================================
    # GLOBAL ACTIONS
    # ====================================================================
    def on_drive_changed(self, choice):
        self.backend.set_drive(choice)
        self.refresh_connection()
        self.refresh_installed_slots()
        self.refresh_irs_list()

    def refresh_connection(self):
        drives = get_available_drives()
        self.drive_menu.configure(values=drives if drives else ["E:"])
        
        if self.backend.is_connected():
            free_gb = self.backend.get_free_space_gb()
            self.status_badge.configure(
                text=f"🟢 MX5 Conectada ({self.backend.drive}) · {free_gb:.1f} GB Livres",
                fg_color="#14532d",
                text_color="#86efac"
            )
        else:
            self.status_badge.configure(
                text="🔴 MX5 Desconectada",
                fg_color="#7f1d1d",
                text_color="#fca5a5"
            )

    def trigger_backup(self):
        if not self.backend.is_connected():
            messagebox.showerror("Erro", "Pedaleira desconectada. Conecte via USB para fazer backup.")
            return
        try:
            bdir = self.backend.backup()
            messagebox.showinfo(
                "Backup Realizado com Sucesso!",
                f"O backup completo dos seus modelos NAM e Presets foi salvo em:\n\n{bdir}"
            )
        except Exception as e:
            messagebox.showerror("Erro no Backup", str(e))

def main():
    app = HeadRushApp()
    app.mainloop()

if __name__ == "__main__":
    main()

