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

# Import headrush_manager
try:
    import headrush_manager as hm
except ImportError:
    # Handle if running from different working directory
    sys.path.insert(0, os.path.dirname(__file__))
    import headrush_manager as hm

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
    if os.path.exists("E:/NAM") or os.path.exists("E:/Blocks"):
        return "E:"
    # Check all other mounted drives
    for d in get_available_drives():
        if os.path.exists(os.path.join(d, "NAM")) or os.path.exists(os.path.join(d, "Blocks")):
            return d
    return None

class HeadRushBackend:
    """Backend wrapper delegating directly to the robust headrush_manager library."""
    def __init__(self, drive="E:"):
        self.set_drive(drive)
        
    def set_drive(self, drive):
        self.drive = drive
        hm.set_drive(drive)
        
    @property
    def nam_dir(self):
        return hm.get_nam_dir()
        
    @property
    def blocks_v1_dir(self):
        return hm.get_blocks_v1_dir()
        
    @property
    def blocks_v2_dir(self):
        return hm.get_blocks_v2_dir()
        
    @property
    def ir_dir(self):
        return hm.get_ir_dir()
        
    @property
    def ir_blocks_dir(self):
        return hm.get_ir_blocks_dir()
        
    def is_connected(self):
        return hm.is_headrush_connected()
        
    def get_free_space_gb(self):
        return hm.get_free_space_gb()

    def get_installed_slots(self):
        return hm.get_installed_slots()

    def get_next_free_slot(self):
        return hm.get_next_free_slot()

    def sanitize_preset_name(self, text, max_len=26):
        return hm.sanitize_for_headrush(text, max_len)

    def create_block_preset(self, slot_num, preset_name, tone=50, level=70):
        paths = hm.create_block_preset(slot_num, preset_name, tone=tone, level=level)
        return paths[0] if paths else None

    def install_model(self, src_path, preset_name=None, slot=None, tone=50, level=70):
        return hm.install_nam_to_headrush(src_path, custom_name=preset_name, slot=slot, tone=tone, level=level)

    def delete_slot(self, slot_num):
        return hm.delete_slot(slot_num)

    def update_slot_trims(self, slot_num, preset_name, tone, level, sync_nam=True):
        return hm.update_slot_trims(slot_num, preset_name, tone=tone, level=level, sync_nam_name=sync_nam)

    def move_slot(self, old_slot, new_slot):
        return hm.move_slot(old_slot, new_slot)

    def get_irs(self):
        return hm.get_available_irs()

    def create_ir_block(self, preset_name, ir_folder, ir_name, gain=-10.0, hi_cut=10000, lo_cut=50):
        return hm.create_ir_block_preset(preset_name, ir_folder, ir_name, gain=gain, hi_cut=hi_cut, lo_cut=lo_cut)

    def sync_missing_blocks(self):
        return hm.sync_missing_blocks()

    def clean_orphaned_blocks(self):
        return hm.clean_orphaned_blocks()

    def defrag_and_reorder_slots(self, sort_by="current", make_safety_backup=True):
        return hm.defrag_and_reorder_slots(sort_by=sort_by, make_safety_backup=make_safety_backup)

    def backup(self):
        return hm.create_backup()

    def list_backups(self):
        return hm.list_backups()

    def restore_backup(self, backup_dir):
        return hm.restore_backup(backup_dir)

class HeadRushApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("HeadRush MX5 · NAM Studio Pro")
        self.geometry("1140x760")
        self.minsize(980, 640)
        
        # Detect drive
        detected_drive = detect_headrush_drive() or "E:"
        self.backend = HeadRushBackend(detected_drive)
        
        # Build UI
        self.build_header()
        self.build_tabs()
        
        # Initial refresh
        self.refresh_connection()
        self.refresh_installed_slots()

    def build_header(self):
        header = ctk.CTkFrame(self, height=65, corner_radius=0, fg_color="#18181b")
        header.pack(fill="x", side="top")
        
        # Logo & Title
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)
        
        lbl_title = ctk.CTkLabel(
            title_box, 
            text="⚡ HEADRUSH NAM STUDIO PRO", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f4f4f5"
        )
        lbl_title.pack(side="left")
        
        lbl_badge = ctk.CTkLabel(
            title_box,
            text="v1.1.0",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#27272a",
            text_color="#a1a1aa",
            corner_radius=6,
            width=50,
            height=20
        )
        lbl_badge.pack(side="left", padx=(10, 0))

        # Status & Controls Box (Right)
        ctrl_box = ctk.CTkFrame(header, fg_color="transparent")
        ctrl_box.pack(side="right", padx=20, pady=12)
        
        # Status Badge
        self.status_badge = ctk.CTkLabel(
            ctrl_box,
            text="Verificando...",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8,
            width=160,
            height=30
        )
        self.status_badge.pack(side="left", padx=8)
        
        # Drive selector
        drives = get_available_drives()
        self.drive_menu = ctk.CTkOptionMenu(
            ctrl_box,
            values=drives if drives else ["E:"],
            width=70,
            command=self.on_drive_changed
        )
        self.drive_menu.set(self.backend.drive)
        self.drive_menu.pack(side="left", padx=6)
        
        # Refresh Button
        btn_refresh = ctk.CTkButton(
            ctrl_box,
            text="🔄",
            width=36,
            height=30,
            font=ctk.CTkFont(size=14),
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=self.refresh_all
        )
        btn_refresh.pack(side="left", padx=6)
        
        # Backup Button
        btn_backup = ctk.CTkButton(
            ctrl_box,
            text="💾 Backup",
            width=90,
            height=30,
            fg_color="#0284c7",
            hover_color="#0369a1",
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
        self.tab_backups = self.tabview.add("  💾 Backups & Restauração  ")
        self.tab_help = self.tabview.add("  ℹ️ Instruções e Ajuda  ")
        
        self.setup_installed_tab()
        self.setup_catalog_tab()
        self.setup_irs_tab()
        self.setup_backups_tab()
        self.setup_help_tab()

    def refresh_all(self):
        self.refresh_connection()
        self.refresh_installed_slots()
        self.refresh_irs_list()
        self.refresh_backups_list()

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
            width=220
        )
        self.ent_filter_installed.pack(side="right", padx=(6, 16), pady=10)
        self.ent_filter_installed.bind("<KeyRelease>", lambda e: self.filter_installed_slots())
        
        btn_organize = ctk.CTkButton(
            top_bar,
            text="🧙 Organizar Timbres",
            width=150,
            height=30,
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.open_organize_dialog
        )
        btn_organize.pack(side="right", padx=6, pady=10)

        btn_sync = ctk.CTkButton(
            top_bar,
            text="🛠️ Sincronizar Blocos",
            width=150,
            height=30,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.trigger_sync_blocks
        )
        btn_sync.pack(side="right", padx=6, pady=10)
        
        # Scrollable container for slots
        self.slots_scroll = ctk.CTkScrollableFrame(self.tab_installed, fg_color="transparent")
        self.slots_scroll.pack(fill="both", expand=True, padx=6, pady=6)

    def trigger_sync_blocks(self):
        if not self.backend.is_connected():
            messagebox.showerror("Erro", "Pedaleira não detectada.")
            return
        count = self.backend.sync_missing_blocks()
        self.refresh_installed_slots()
        messagebox.showinfo(
            "Sincronização de Blocos",
            f"Varredura concluída!\n\n"
            f"• {count} blocos de presets foram gerados/reparados para arquivos .nam que estavam sem preset."
        )

    def open_organize_dialog(self):
        if not self.backend.is_connected():
            messagebox.showerror("Erro", "Pedaleira não conectada via USB.")
            return
            
        slots = self.backend.get_installed_slots()
        occupied = [info for s, info in slots.items() if info.get('nam_file')]
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("🧙 Assistente de Organização · HeadRush NAM Studio")
        dialog.geometry("520x460")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(
            dialog,
            text="🧙 Assistente de Organização da Pedaleira",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#a855f7"
        ).pack(pady=(16, 4))
        
        ctk.CTkLabel(
            dialog,
            text=f"Total de timbres ativos na HeadRush: {len(occupied)} modelos instalados.",
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa"
        ).pack(pady=(0, 12))
        
        # Options Frame
        opts_frame = ctk.CTkFrame(dialog, fg_color="#18181b", corner_radius=8)
        opts_frame.pack(fill="x", padx=25, pady=8)
        
        mode_var = ctk.StringVar(value="current")
        
        r1 = ctk.CTkRadioButton(
            opts_frame,
            text="📦 Compactar Slots (Remover Espaços Vazios)\nRenumera todos os timbres de 000 em diante sem deixar buracos.",
            variable=mode_var,
            value="current",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffffff"
        )
        r1.pack(anchor="w", padx=16, pady=12)
        
        r2 = ctk.CTkRadioButton(
            opts_frame,
            text="🔤 Ordenar Alfabeticamente (A ➔ Z)\nOrganiza todos os timbres em ordem alfabética (000 a N-1).",
            variable=mode_var,
            value="alpha",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffffff"
        )
        r2.pack(anchor="w", padx=16, pady=12)
        
        chk_backup = ctk.CTkCheckBox(
            dialog,
            text="Criar Backup Automático de Segurança antes de organizar",
            font=ctk.CTkFont(size=12),
            text_color="#e4e4e7"
        )
        chk_backup.select()
        chk_backup.pack(anchor="w", padx=28, pady=8)
        
        # Clean orphans button
        def do_clean_orphans():
            deleted = self.backend.clean_orphaned_blocks()
            self.refresh_installed_slots()
            messagebox.showinfo(
                "Limpeza de Presets Órfãos",
                f"Varredura de limpeza concluída!\n\n"
                f"• {len(deleted)} blocos órfãos (sem arquivo .nam correspondente) foram removidos."
            )
            
        btn_clean = ctk.CTkButton(
            dialog,
            text="🧹 Limpar Presets Órfãos (Blocos sem arquivo .nam)",
            fg_color="#27272a",
            hover_color="#3f3f46",
            height=30,
            command=do_clean_orphans
        )
        btn_clean.pack(fill="x", padx=25, pady=4)
        
        def run_organize():
            mode = mode_var.get()
            make_bk = bool(chk_backup.get())
            
            mode_desc = "Compactação de Slots (000 a N-1)" if mode == "current" else "Ordenação Alfabética (A-Z)"
            ans = messagebox.askyesno(
                "Confirmar Reorganização",
                f"Você escolheu: {mode_desc}\n\n"
                f"Todos os seus {len(occupied)} timbres serão reindexados e organizados sequencialmente a partir do Slot 000.\n"
                f"Deseja prosseguir?"
            )
            if not ans:
                return
                
            try:
                res = self.backend.defrag_and_reorder_slots(sort_by=mode, make_safety_backup=make_bk)
                dialog.destroy()
                self.refresh_all()
                
                msg = f"Reorganização concluída com sucesso! 🚀\n\n" \
                      f"• {res['count']} timbres organizados sequencialmente (Slots 000 a {res['count']-1:03d}).\n"
                if res.get('backup'):
                    msg += f"• Backup de segurança salvo em: {res['backup']}\n\n"
                msg += "⚠️ LEMBRE-SE: Reinicie sua HeadRush MX5 para que ela reconheça a nova ordem dos slots!"
                
                messagebox.showinfo("Sucesso!", msg)
            except Exception as e:
                messagebox.showerror("Erro ao Organizar", str(e))
                
        btn_start = ctk.CTkButton(
            dialog,
            text="🚀 Iniciar Reorganização",
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            command=run_organize
        )
        btn_start.pack(fill="x", padx=25, pady=(12, 10))

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
                text="Pedaleira não detectada.\nConecte o cabo USB da HeadRush MX5 no modo USB Transfer e clique em 🔄 Atualizar.",
                font=ctk.CTkFont(size=15),
                text_color="#71717a"
            )
            empty_lbl.pack(pady=60)
            return

        filter_text = self.ent_filter_installed.get().strip().lower()
        
        if not slots:
            ctk.CTkLabel(
                self.slots_scroll,
                text="Nenhum timbre instalado ainda na pasta /NAM.\nVá na aba 'Catálogo TONE3000' para instalar modelos com 1 clique!",
                font=ctk.CTkFont(size=14),
                text_color="#71717a"
            ).pack(pady=50)
            return
            
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
        
        # Actions Box
        actions_box = ctk.CTkFrame(row, fg_color="transparent")
        actions_box.pack(side="right", padx=6)
        
        btn_edit = ctk.CTkButton(
            actions_box,
            text="✏️ Trims / Editar",
            width=110,
            height=28,
            fg_color="#27272a",
            hover_color="#3f3f46",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda s=info['slot']: self.open_edit_dialog(s)
        )
        btn_edit.pack(side="left", padx=4)

        btn_move = ctk.CTkButton(
            actions_box,
            text="🚚 Mover",
            width=70,
            height=28,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=12),
            command=lambda s=info['slot']: self.open_move_dialog(s)
        )
        btn_move.pack(side="left", padx=4)
        
        btn_del = ctk.CTkButton(
            actions_box,
            text="🗑️",
            width=36,
            height=28,
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            command=lambda s=info['slot']: self.confirm_delete_slot(s)
        )
        btn_del.pack(side="left", padx=4)

    def filter_installed_slots(self):
        self.refresh_installed_slots()

    def open_edit_dialog(self, slot_num):
        """Advanced modal dialog to edit preset name, Tone/Level trims, with live sliders and number inputs."""
        slots = self.backend.get_installed_slots()
        if slot_num not in slots:
            messagebox.showerror("Erro", f"Slot {slot_num:03d} não foi encontrado.")
            return
        info = slots[slot_num]
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Ajustar Preset & Trims · Slot {slot_num:03d}")
        dialog.geometry("480x460")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(
            dialog,
            text=f"🎛️ Calibrar Timbre - Slot {slot_num:03d}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8"
        ).pack(pady=(16, 4))
        
        # Name Frame
        name_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        name_frame.pack(fill="x", padx=25, pady=(8, 4))
        ctk.CTkLabel(name_frame, text="Nome do Preset (Visor da MX5):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        ent_name = ctk.CTkEntry(name_frame, height=32, font=ctk.CTkFont(size=13))
        ent_name.insert(0, info.get('preset_name') or info.get('nam_name') or "")
        ent_name.pack(fill="x", pady=4)
        
        chk_sync_nam = ctk.CTkCheckBox(
            name_frame, 
            text="Sincronizar e renomear arquivo .nam em /NAM",
            font=ctk.CTkFont(size=11),
            text_color="#a1a1aa"
        )
        chk_sync_nam.select()
        chk_sync_nam.pack(anchor="w", pady=(2, 8))

        # Tone Trim Box (Input Gain)
        tone_box = ctk.CTkFrame(dialog, fg_color="#18181b", corner_radius=8)
        tone_box.pack(fill="x", padx=25, pady=6)
        
        top_tone = ctk.CTkFrame(tone_box, fg_color="transparent")
        top_tone.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(top_tone, text="Tone Knob (Input Trim / Ganho de Entrada):", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        lbl_tone_val = ctk.CTkLabel(top_tone, text=f"{info.get('tone', 50)}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#f59e0b")
        lbl_tone_val.pack(side="right")
        
        slider_tone = ctk.CTkSlider(tone_box, from_=0, to=100, number_of_steps=100)
        slider_tone.set(info.get('tone', 50))
        slider_tone.pack(fill="x", padx=10, pady=(4, 8))
        slider_tone.configure(command=lambda v: lbl_tone_val.configure(text=str(int(v))))

        # Level Trim Box (Output Volume)
        level_box = ctk.CTkFrame(dialog, fg_color="#18181b", corner_radius=8)
        level_box.pack(fill="x", padx=25, pady=6)
        
        top_level = ctk.CTkFrame(level_box, fg_color="transparent")
        top_level.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(top_level, text="Level Knob (Output Trim / Volume Geral):", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        lbl_level_val = ctk.CTkLabel(top_level, text=f"{info.get('level', 70)}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#10b981")
        lbl_level_val.pack(side="right")
        
        slider_level = ctk.CTkSlider(level_box, from_=0, to=100, number_of_steps=100)
        slider_level.set(info.get('level', 70))
        slider_level.pack(fill="x", padx=10, pady=(4, 8))
        slider_level.configure(command=lambda v: lbl_level_val.configure(text=str(int(v))))

        # Quick Preset Buttons
        quick_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        quick_frame.pack(fill="x", padx=25, pady=4)
        
        def reset_defaults():
            slider_tone.set(50)
            lbl_tone_val.configure(text="50")
            slider_level.set(70)
            lbl_level_val.configure(text="70")
            
        btn_reset = ctk.CTkButton(
            quick_frame,
            text="🔄 Redefinir Padrão (50 / 70)",
            fg_color="#27272a",
            hover_color="#3f3f46",
            height=26,
            font=ctk.CTkFont(size=11),
            command=reset_defaults
        )
        btn_reset.pack(side="left")

        # Save Button
        def save():
            new_name = ent_name.get().strip()
            if not new_name:
                messagebox.showwarning("Aviso", "O nome do preset não pode ficar vazio.")
                return
                
            tone_val = int(slider_tone.get())
            level_val = int(slider_level.get())
            sync_val = bool(chk_sync_nam.get())
            
            try:
                self.backend.update_slot_trims(slot_num, new_name, tone_val, level_val, sync_nam=sync_val)
                dialog.destroy()
                self.refresh_installed_slots()
                messagebox.showinfo(
                    "Ajustes Salvos com Sucesso! 🎛️",
                    f"Slot {slot_num:03d} atualizado:\n\n"
                    f"• Nome: {new_name}\n"
                    f"• Tone (Input Trim): {tone_val}\n"
                    f"• Level (Volume): {level_val}\n\n"
                    f"⚠️ Lembre-se: se você alterou o nome do arquivo, reinicie a pedaleira para atualizar o visor."
                )
            except Exception as e:
                messagebox.showerror("Erro ao Salvar", str(e))
            
        btn_save = ctk.CTkButton(
            dialog, 
            text="💾 Salvar Alterações", 
            fg_color="#16a34a", 
            hover_color="#15803d", 
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36,
            command=save
        )
        btn_save.pack(fill="x", padx=25, pady=(12, 10))

    def open_move_dialog(self, old_slot):
        """Allows reassigning a model to another slot."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Mover Slot {old_slot:03d}")
        dialog.geometry("380x260")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        slots = self.backend.get_installed_slots()
        info = slots.get(old_slot, {})
        pname = info.get('preset_name') or f"Slot {old_slot:03d}"
        
        ctk.CTkLabel(
            dialog,
            text=f"Mover '{pname}' (Slot {old_slot:03d})",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(16, 8))
        
        ctk.CTkLabel(dialog, text="Selecione o novo Slot de Destino (000-100):").pack(anchor="w", padx=25)
        
        slot_options = [f"{s:03d} {'(Ocupado)' if s in slots else '(Livre)'}" for s in range(101)]
        opt_slots = ctk.CTkOptionMenu(dialog, values=slot_options, height=32)
        # Default to first free slot
        next_free = self.backend.get_next_free_slot()
        if next_free is not None:
            opt_slots.set(f"{next_free:03d} (Livre)")
        opt_slots.pack(fill="x", padx=25, pady=8)
        
        def do_move():
            val_str = opt_slots.get().split()[0]
            new_s = int(val_str)
            if new_s == old_slot:
                dialog.destroy()
                return
                
            if new_s in slots:
                ans = messagebox.askyesno(
                    "Substituir Slot",
                    f"O Slot {new_s:03d} já contém '{slots[new_s].get('preset_name')}'.\nDeseja substituir esse timbre?"
                )
                if not ans:
                    return
                    
            try:
                self.backend.move_slot(old_slot, new_s)
                dialog.destroy()
                self.refresh_installed_slots()
                messagebox.showinfo("Sucesso", f"Timbre movido para o Slot {new_s:03d} com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro ao Mover", str(e))
                
        btn_confirm = ctk.CTkButton(dialog, text="Mover Agora", fg_color="#0284c7", hover_color="#0369a1", command=do_move)
        btn_confirm.pack(fill="x", padx=25, pady=16)

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
        # Search controls frame
        search_frame = ctk.CTkFrame(self.tab_catalog, fg_color="#1e1e24", corner_radius=8)
        search_frame.pack(fill="x", padx=10, pady=8)
        
        # Search entry
        self.ent_search = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Busque por amplificador, pedal, artista (ex: 5150, Dumble, Petrucci, Klon, Bogner)...",
            height=36,
            font=ctk.CTkFont(size=13)
        )
        self.ent_search.pack(side="left", fill="x", expand=True, padx=(12, 6), pady=10)
        self.ent_search.bind("<Return>", lambda e: self.do_search())
        
        # Category Filter
        self.opt_category = ctk.CTkOptionMenu(
            search_frame,
            values=["Todos os Tipos", "Cabeçote / Amp", "Pedal de Drive", "Amp + Gabinete"],
            width=140,
            height=36,
            command=lambda v: self.do_search()
        )
        self.opt_category.pack(side="left", padx=4, pady=10)
        
        # Architecture Filter
        self.opt_arch = ctk.CTkOptionMenu(
            search_frame,
            values=["Todas Arquiteturas", "A2 Slim (Recomendado MX5)", "v1 Standard"],
            width=180,
            height=36,
            command=lambda v: self.do_search()
        )
        self.opt_arch.pack(side="left", padx=4, pady=10)
        
        # Search Button
        btn_search = ctk.CTkButton(
            search_frame,
            text="Buscar",
            width=90,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.do_search
        )
        btn_search.pack(side="left", padx=(4, 12), pady=10)
        
        # Quick Tags Bar
        tags_bar = ctk.CTkFrame(self.tab_catalog, fg_color="transparent")
        tags_bar.pack(fill="x", padx=10, pady=(0, 4))
        
        quick_tags = ["5150", "Dumble", "Petrucci", "Andy Timmons", "1981 DRV", "Mesa Boogie", "Bogner", "Friedman", "Marshall", "Soldano", "Klon", "King of Tone", "TS808"]
        for tag in quick_tags:
            btn_tag = ctk.CTkButton(
                tags_bar,
                text=tag,
                height=24,
                font=ctk.CTkFont(size=11),
                fg_color="#27272a",
                hover_color="#3f3f46",
                command=lambda t=tag: self.quick_search(t)
            )
            btn_tag.pack(side="left", padx=2, pady=2)
            
        # Catalog Results Scroll
        self.catalog_scroll = ctk.CTkScrollableFrame(self.tab_catalog, fg_color="transparent")
        self.catalog_scroll.pack(fill="both", expand=True, padx=6, pady=4)
        
        # Initial search
        self.quick_search("Dumble")

    def quick_search(self, query):
        self.ent_search.delete(0, 'end')
        self.ent_search.insert(0, query)
        self.do_search()

    def do_search(self):
        query = self.ent_search.get().strip()
        if not query:
            return
            
        for widget in self.catalog_scroll.winfo_children():
            widget.destroy()
            
        if not os.path.exists(DB_PATH):
            ctk.CTkLabel(
                self.catalog_scroll,
                text=f"Banco de dados Tone3000 não encontrado em:\n{DB_PATH}",
                font=ctk.CTkFont(size=14),
                text_color="#ef4444"
            ).pack(pady=40)
            return

        cat_choice = self.opt_category.get()
        cat_map = {
            "Cabeçote / Amp": "amp",
            "Pedal de Drive": "pedal",
            "Amp + Gabinete": "amp-cab"
        }
        target_gear = cat_map.get(cat_choice)
        
        arch_choice = self.opt_arch.get()
        arch_filter = None
        if "A2" in arch_choice:
            arch_filter = '2'
        elif "v1" in arch_choice:
            arch_filter = '1'

        try:
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
            
            if target_gear:
                sql += ' AND t.gear = ?'
                params.append(target_gear)
                
            if arch_filter:
                sql += ' AND m.architecture_version = ?'
                params.append(arch_filter)
                
            sql += ' LIMIT 40'
            cur.execute(sql, params)
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            ctk.CTkLabel(
                self.catalog_scroll,
                text=f"Erro na consulta SQL: {e}",
                text_color="#ef4444"
            ).pack(pady=20)
            return

        if not rows:
            ctk.CTkLabel(
                self.catalog_scroll,
                text=f"Nenhum modelo encontrado para '{query}'.\nTente buscar com termos mais gerais (ex: Marshall, Drive, Clean, Lead).",
                font=ctk.CTkFont(size=14),
                text_color="#71717a"
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
        
        installed_slots = self.backend.get_installed_slots()
        installed_names = {info.get('preset_name', '').lower(): s for s, info in installed_slots.items()}
        
        for r in rows:
            m_id, m_name, t_title, creator, a_ver, gear, rel_path, desc = r
            is_installed = m_name.lower() in installed_names
            installed_slot = installed_names.get(m_name.lower())
            self.create_catalog_card(m_id, m_name, t_title, creator, a_ver, gear, rel_path, is_installed, installed_slot)

    def create_catalog_card(self, m_id, m_name, t_title, creator, a_ver, gear, rel_path, is_installed=False, installed_slot=None):
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
        
        title_box = ctk.CTkFrame(info_box, fg_color="transparent")
        title_box.pack(anchor="w")
        
        title_lbl = ctk.CTkLabel(
            title_box,
            text=m_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff"
        )
        title_lbl.pack(side="left")
        
        if is_installed:
            inst_badge = ctk.CTkLabel(
                title_box,
                text=f"✓ Instalado (Slot {installed_slot:03d})",
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color="#065f46",
                text_color="#a7f3d0",
                corner_radius=4,
                width=120,
                height=18
            )
            inst_badge.pack(side="left", padx=8)
        
        gear_pt = {"amp": "Cabeçote", "pedal": "Pedal", "amp-cab": "Amp + Caixa", "outboard": "Outboard"}.get(gear, gear)
        desc_lbl = ctk.CTkLabel(
            info_box,
            text=f"Pacote: {t_title}  ·  Criador: {creator}  ·  Tipo: {gear_pt}",
            font=ctk.CTkFont(size=11),
            text_color="#a1a1aa",
            anchor="w"
        )
        desc_lbl.pack(anchor="w")
        
        # Install Button Box
        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.pack(side="right", padx=12, pady=10)
        
        btn_send = ctk.CTkButton(
            btn_box,
            text="⚡ Enviar p/ MX5",
            width=130,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=lambda p=rel_path, n=m_name: self.install_model_action(p, n)
        )
        btn_send.pack(side="left", padx=2)

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
    # TAB 4: BACKUPS & RESTAURAÇÃO
    # ====================================================================
    def setup_backups_tab(self):
        top_bar = ctk.CTkFrame(self.tab_backups, fg_color="#1e1e24", corner_radius=8)
        top_bar.pack(fill="x", padx=10, pady=8)
        
        ctk.CTkLabel(
            top_bar,
            text="💾 Gerenciador de Backups & Restauração",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8"
        ).pack(side="left", padx=16, pady=10)
        
        btn_new_backup = ctk.CTkButton(
            top_bar,
            text="➕ Criar Novo Backup Agora",
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.trigger_backup
        )
        btn_new_backup.pack(side="right", padx=16, pady=10)
        
        self.backups_scroll = ctk.CTkScrollableFrame(self.tab_backups, fg_color="transparent")
        self.backups_scroll.pack(fill="both", expand=True, padx=6, pady=6)
        
        self.refresh_backups_list()

    def refresh_backups_list(self):
        for widget in self.backups_scroll.winfo_children():
            widget.destroy()
            
        backups = self.backend.list_backups()
        if not backups:
            ctk.CTkLabel(
                self.backups_scroll,
                text="Nenhum backup encontrado ainda.\nClique em 'Criar Novo Backup Agora' para salvar um snapshot da sua pedaleira.",
                font=ctk.CTkFont(size=14),
                text_color="#71717a"
            ).pack(pady=50)
            return
            
        for b in backups:
            card = ctk.CTkFrame(self.backups_scroll, fg_color="#18181b", corner_radius=8)
            card.pack(fill="x", pady=4, padx=4)
            
            info_box = ctk.CTkFrame(card, fg_color="transparent")
            info_box.pack(side="left", fill="x", expand=True, padx=12, pady=10)
            
            ctk.CTkLabel(
                info_box,
                text=f"📦 {b['name']}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#ffffff",
                anchor="w"
            ).pack(anchor="w")
            
            ctk.CTkLabel(
                info_box,
                text=f"Caminho: {b['path']}",
                font=ctk.CTkFont(size=11),
                text_color="#71717a",
                anchor="w"
            ).pack(anchor="w")
            
            btn_restore = ctk.CTkButton(
                card,
                text="♻️ Restaurar p/ MX5",
                width=140,
                height=30,
                fg_color="#d97706",
                hover_color="#b45309",
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda p=b['path']: self.confirm_restore_backup(p)
            )
            btn_restore.pack(side="right", padx=12, pady=10)

    def confirm_restore_backup(self, backup_dir):
        if not self.backend.is_connected():
            messagebox.showerror("Erro", "Pedaleira desconectada. Conecte no modo USB para restaurar.")
            return
            
        ans = messagebox.askyesno(
            "Confirmar Restauração",
            f"Atenção! Restaurar este backup substituirá todos os timbres e blocos atuais da sua pedaleira.\n\n"
            f"Origem do Backup:\n{backup_dir}\n\nDeseja continuar?"
        )
        if ans:
            try:
                self.backend.restore_backup(backup_dir)
                self.refresh_installed_slots()
                messagebox.showinfo("Restauração Concluída", "Backup restaurado com sucesso para a HeadRush MX5!\n\nLembre-se de reiniciar a pedaleira.")
            except Exception as e:
                messagebox.showerror("Erro na Restauração", str(e))

    # ====================================================================
    # TAB 5: HELP & INSTRUCTIONS
    # ====================================================================
    def setup_help_tab(self):
        frame = ctk.CTkScrollableFrame(self.tab_help, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        
        help_text = """
# 🎸 GUIA COMPLETO · HEADRUSH NAM STUDIO PRO

### 🔌 1. Como Conectar e Desconectar a MX5
1. Conecte a pedaleira ao PC com o cabo USB.
2. Na tela da MX5, toque nos 3 pontinhos (Menu Global) -> **USB Transfer**.
3. A pedaleira aparecerá como uma unidade removível (geralmente `E:`).
4. Para desconectar com segurança: toque em **Sync / Eject** na tela da pedaleira antes de remover o cabo.
5. **IMPORTANTE**: Após transferir novos timbres, reinicie a pedaleira (desligue e ligue no botão) para que o firmware leia os novos arquivos da pasta `/NAM`.

---

### 🎛️ 2. Como Tocar os Timbres na MX5
1. Em qualquer Rig, adicione o pedal **Anxiety OD V2** (ou **Anxiety OD**).
2. Toque no pedal e abra a lista de **Presets**.
3. Você verá todos os seus presets numerados exatamente com o slot (ex.: `028 - 1981 DRV MED GAIN`, `031 - DUMBLE SSS CLEAN EVM`).
4. Ao selecionar o preset:
   - O botão **DRIVE** irá exatamente para a posição do modelo NAM!
   - O botão **TONE** funciona como ajuste fino de ganho de entrada (**Input Trim**).
   - O botão **LEVEL** funciona como volume final (**Output Trim**).

---

### ✏️ 3. Como Editar Presets e Trims no App
- Na aba **Minha Pedaleira**, clique no botão **✏️ Trims / Editar** ao lado de qualquer timbre.
- Ajuste os controles de **Tone** e **Level** graficamente.
- Você pode alterar o nome de exibição no visor e sincronizar automaticamente o nome do arquivo `.nam`.
- Se quiser reordenar seus timbres, use o botão **🚚 Mover** para transferir o som para qualquer slot livre de 000 a 100!

---

### 🔊 4. Dica sobre Gabinetes e IRs
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
        self.refresh_all()

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
            self.refresh_backups_list()
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
