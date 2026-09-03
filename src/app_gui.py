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

# Robust module resolution for frozen executable and source scripts
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

if getattr(sys, 'frozen', False):
    _BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    if _BUNDLE_DIR not in sys.path:
        sys.path.insert(0, _BUNDLE_DIR)
    _SRC_BUNDLE = os.path.join(_BUNDLE_DIR, "src")
    if os.path.exists(_SRC_BUNDLE) and _SRC_BUNDLE not in sys.path:
        sys.path.insert(0, _SRC_BUNDLE)

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
    try:
        from src import headrush_manager as hm
    except ImportError:
        import importlib.util
        hm_path = os.path.join(_CURRENT_DIR, "headrush_manager.py")
        if not os.path.exists(hm_path) and getattr(sys, 'frozen', False):
            hm_path = os.path.join(getattr(sys, '_MEIPASS', ''), "headrush_manager.py")
        spec = importlib.util.spec_from_file_location("headrush_manager", hm_path)
        hm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hm)

# App Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

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

    def install_model(self, src_path, preset_name=None, slot=None, tone=50, level=70, custom_name=None):
        final_name = preset_name or custom_name
        return hm.install_nam_to_headrush(src_path, custom_name=final_name, slot=slot, tone=tone, level=level)

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

    def smart_format_preset_name(self, name, max_len=24):
        return hm.smart_format_preset_name(name, max_len)

    def inspect_nam_file(self, filepath):
        return hm.inspect_nam_file(filepath)

    def detect_duplicate_models(self):
        return hm.detect_duplicate_models()

    def import_local_models_batch(self, paths, base_slot=None, smart_rename=True):
        return hm.import_local_models_batch(paths, base_slot=base_slot, smart_rename=smart_rename)

    def save_setlist(self, name):
        return hm.save_setlist(name)

    def list_setlists(self):
        return hm.list_setlists()

    def load_setlist(self, name):
        return hm.load_setlist(name)

    def export_setlist_zip(self, name, target_path):
        return hm.export_setlist_zip(name, target_path)

    def import_setlist_zip(self, zip_path):
        return hm.import_setlist_zip(zip_path)

    def generate_stage_cheat_sheet(self, fmt="html"):
        return hm.generate_stage_cheat_sheet(fmt)

    def get_storage_status(self):
        return hm.get_storage_status()

    def safe_eject(self):
        return hm.safe_eject_headrush()

    def export_slot_bundle(self, slot_num, target_path):
        return hm.export_slot_bundle(slot_num, target_path)

    def apply_trim_preset(self, slot_num, preset_type):
        return hm.apply_trim_preset(slot_num, preset_type)

    def perform_health_check(self):
        return hm.perform_health_check()

    def cloud_search(self, query="", gear=None, page=1):
        return hm.cloud_search_tones(query=query, gear=gear, page=page)

    def cloud_trending(self, gear=None):
        return hm.cloud_get_trending(gear=gear)

    def cloud_latest(self, gear=None):
        return hm.cloud_get_latest(gear=gear)

    def cloud_models(self, tone_id):
        return hm.cloud_get_tone_models(tone_id)

    def cloud_install(self, model_obj, slot=None, custom_name=None, tone=50, level=70):
        return hm.cloud_download_and_install(model_obj, slot=slot, custom_name=custom_name, tone=tone, level=level)

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
            text="v1.3 · Gratuito",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#16a34a",
            text_color="#ffffff",
            corner_radius=6,
            width=90,
            height=20
        )
        lbl_badge.pack(side="left", padx=(10, 0))

        lbl_dev = ctk.CTkLabel(
            title_box,
            text="⚡ Em Desenvolvimento",
            font=ctk.CTkFont(size=11),
            fg_color="#27272a",
            text_color="#fbbf24",
            corner_radius=6,
            width=140,
            height=20
        )
        lbl_dev.pack(side="left", padx=(6, 0))

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
            width=85,
            height=30,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.trigger_backup
        )
        btn_backup.pack(side="left", padx=4)

        # Safe Eject Button
        btn_eject = ctk.CTkButton(
            ctrl_box,
            text="⏏️ Ejetar",
            width=80,
            height=30,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.trigger_eject
        )
        btn_eject.pack(side="left", padx=4)

        # Coffee / Support Button
        btn_coffee = ctk.CTkButton(
            ctrl_box,
            text="☕ Apoiar / Café",
            width=115,
            height=30,
            fg_color="#d97706",
            hover_color="#b45309",
            text_color="#ffffff",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.show_donation_dialog
        )
        btn_coffee.pack(side="left", padx=4)

    def show_donation_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("☕ Apoie o HeadRush NAM Studio")
        dlg.geometry("540x440")
        dlg.transient(self)
        dlg.grab_set()

        # Header banner
        banner = ctk.CTkFrame(dlg, fg_color="#1e1e24", corner_radius=0)
        banner.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            banner,
            text="☕ Me pague um café para apoiar o projeto!",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f59e0b"
        ).pack(anchor="w", padx=20, pady=(16, 4))

        ctk.CTkLabel(
            banner,
            text="Software 100% Gratuito, Aberto e em Desenvolvimento Ativo",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        ).pack(anchor="w", padx=20, pady=(0, 14))

        # Content body
        body = ctk.CTkFrame(dlg, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=16)

        msg = (
            "🎸 O HeadRush NAM Studio foi criado por amor à música e para libertar "
            "todo o potencial sonoro da HeadRush MX5 com perfis Neural Amp Modeler (NAM), "
            "gerenciamento dos 101 slots, gerador de blocos V1/V2 e acesso à nuvem TONE3000.\n\n"
            "💡 Esta ferramenta é totalmente GRATUITA e está em contínuo desenvolvimento "
            "com novas melhorias e correções sendo lançadas regularmente.\n\n"
            "Se o programa te ajuda nos seus ensaios, gravações ou shows, considere me pagar "
            "um café para ajudar a manter o projeto ativo e apoiar o tempo de desenvolvimento!"
        )
        ctk.CTkLabel(
            body,
            text=msg,
            font=ctk.CTkFont(size=12),
            text_color="#e4e4e7",
            justify="left",
            wraplength=490
        ).pack(anchor="w", pady=(0, 14))

        # PIX box
        pix_frame = ctk.CTkFrame(body, fg_color="#18181b", corner_radius=8, border_width=1, border_color="#3f3f46")
        pix_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(
            pix_frame,
            text="🔑 Chave PIX / Apoio (Qualquer valor é muito bem-vindo!):",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38bdf8"
        ).pack(anchor="w", padx=14, pady=(10, 2))

        pix_row = ctk.CTkFrame(pix_frame, fg_color="transparent")
        pix_row.pack(fill="x", padx=14, pady=(0, 10))

        ent_pix = ctk.CTkEntry(
            pix_row,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        ent_pix.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        default_pix = "tiagojsoares7@gmail.com"
        ent_pix.insert(0, default_pix)

        def _copy_pix():
            self.clipboard_clear()
            self.clipboard_append(ent_pix.get().strip())
            btn_copy.configure(text="✓ Copiado!", fg_color="#16a34a")
            self.after(2000, lambda: btn_copy.configure(text="📋 Copiar PIX", fg_color="#d97706"))

        btn_copy = ctk.CTkButton(
            pix_row,
            text="📋 Copiar PIX",
            width=110,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#d97706",
            hover_color="#b45309",
            command=_copy_pix
        )
        btn_copy.pack(side="left")

        # Bottom buttons
        btn_box = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(0, 16))

        def _open_github():
            import webbrowser
            webbrowser.open("https://github.com/tiagojsoares/headrush-nam-studio")

        ctk.CTkButton(
            btn_box,
            text="⭐ Ver Projeto no GitHub",
            font=ctk.CTkFont(size=12),
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=_open_github
        ).pack(side="left")

        ctk.CTkButton(
            btn_box,
            text="Fechar",
            width=80,
            font=ctk.CTkFont(size=12),
            fg_color="#334155",
            hover_color="#475569",
            command=dlg.destroy
        ).pack(side="right")

    def trigger_eject(self):
        res = self.backend.safe_eject()
        messagebox.showinfo(
            "Ejeção Segura Concluída ⏏️",
            f"{res['message']}\n\n"
            "Passos recomendados:\n"
            "1. Desconecte o cabo USB da sua HeadRush MX5.\n"
            "2. Desligue e ligue a pedaleira no botão para recarregar todos os timbres e blocos!"
        )

    def build_tabs(self):
        self.tabview = ctk.CTkTabview(self, corner_radius=10, fg_color="#121214")
        self.tabview.pack(fill="both", expand=True, padx=16, pady=12)
        
        self.tab_installed = self.tabview.add("  🎸 Minha Pedaleira (Slots 000-100)  ")
        self.tab_setlists = self.tabview.add("  🗂️ Setlists & Cenários  ")
        self.tab_catalog = self.tabview.add("  🔍 Catálogo TONE3000 (97k Timbres)  ")
        self.tab_irs = self.tabview.add("  🔊 Impulse Responses (IRs)  ")
        self.tab_backups = self.tabview.add("  💾 Backups & Restauração  ")
        self.tab_help = self.tabview.add("  ℹ️ Instruções e Ajuda  ")
        
        self.setup_installed_tab()
        self.setup_setlists_tab()
        self.setup_catalog_tab()
        self.setup_irs_tab()
        self.setup_backups_tab()
        self.setup_help_tab()

        # Persistent Footer Banner
        footer = ctk.CTkFrame(self, height=28, fg_color="#18181b", corner_radius=0)
        footer.pack(fill="x", side="bottom")

        lbl_footer_status = ctk.CTkLabel(
            footer,
            text="✨ Software 100% Gratuito · Em Desenvolvimento Ativo para a HeadRush MX5",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        lbl_footer_status.pack(side="left", padx=16, pady=2)

        btn_support_footer = ctk.CTkButton(
            footer,
            text="☕ Apoiar / Me Pague um Café",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="transparent",
            hover_color="#27272a",
            text_color="#f59e0b",
            height=22,
            command=self.show_donation_dialog
        )
        btn_support_footer.pack(side="right", padx=16, pady=2)

    def refresh_all(self):
        self.refresh_connection()
        self.refresh_installed_slots()
        self.refresh_setlists_list()
        self.refresh_irs_list()
        self.refresh_backups_list()

    # ====================================================================
    # TAB 1: INSTALLED SLOTS
    # ====================================================================
    def setup_installed_tab(self):
        self.selected_category = "Todos"
        
        # Row 1: Summary, Search, Sync, Organize
        top_bar = ctk.CTkFrame(self.tab_installed, fg_color="#1e1e24", corner_radius=8)
        top_bar.pack(fill="x", padx=10, pady=(8, 4))
        
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
            width=200
        )
        self.ent_filter_installed.pack(side="right", padx=(6, 16), pady=10)
        self.ent_filter_installed.bind("<KeyRelease>", lambda e: self.filter_installed_slots())
        
        btn_organize = ctk.CTkButton(
            top_bar,
            text="🧙 Organizar",
            width=110,
            height=30,
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.open_organize_dialog
        )
        btn_organize.pack(side="right", padx=4, pady=10)

        btn_sync = ctk.CTkButton(
            top_bar,
            text="🛠️ Sincronizar",
            width=110,
            height=30,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.trigger_sync_blocks
        )
        btn_sync.pack(side="right", padx=4, pady=10)

        # Row 2: Pro Suite Actions & Category Filters
        tools_bar = ctk.CTkFrame(self.tab_installed, fg_color="#18181b", corner_radius=8)
        tools_bar.pack(fill="x", padx=10, pady=4)
        
        btn_batch = ctk.CTkButton(
            tools_bar,
            text="📂 Importar Pack PC",
            width=140,
            height=28,
            fg_color="#059669",
            hover_color="#047857",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.open_batch_import_dialog
        )
        btn_batch.pack(side="left", padx=(10, 4), pady=6)

        btn_cheat = ctk.CTkButton(
            tools_bar,
            text="📋 Guia de Palco",
            width=120,
            height=28,
            fg_color="#27272a",
            hover_color="#3f3f46",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.open_cheatsheet_dialog
        )
        btn_cheat.pack(side="left", padx=4, pady=6)

        btn_health = ctk.CTkButton(
            tools_bar,
            text="❤️ Saúde",
            width=90,
            height=28,
            fg_color="#27272a",
            hover_color="#3f3f46",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.open_health_dialog
        )
        btn_health.pack(side="left", padx=4, pady=6)

        btn_dupes = ctk.CTkButton(
            tools_bar,
            text="🔍 Duplicados",
            width=100,
            height=28,
            fg_color="#27272a",
            hover_color="#3f3f46",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.open_duplicates_dialog
        )
        btn_dupes.pack(side="left", padx=4, pady=6)

        # Category Chips (Right side of tools_bar)
        chips_box = ctk.CTkFrame(tools_bar, fg_color="transparent")
        chips_box.pack(side="right", padx=10, pady=6)
        
        self.chip_btns = {}
        for cat in ["Todos", "Amps", "Drives", "Clean", "Signature"]:
            btn = ctk.CTkButton(
                chips_box,
                text=cat,
                width=65,
                height=24,
                font=ctk.CTkFont(size=11),
                fg_color="#38bdf8" if cat == "Todos" else "#27272a",
                text_color="#0f172a" if cat == "Todos" else "#e4e4e7",
                hover_color="#0284c7",
                command=lambda c=cat: self.select_category_chip(c)
            )
            btn.pack(side="left", padx=2)
            self.chip_btns[cat] = btn

        # Scrollable container for slots
        self.slots_scroll = ctk.CTkScrollableFrame(self.tab_installed, fg_color="transparent")
        self.slots_scroll.pack(fill="both", expand=True, padx=6, pady=4)

    def select_category_chip(self, category):
        self.selected_category = category
        for cat, btn in self.chip_btns.items():
            if cat == category:
                btn.configure(fg_color="#38bdf8", text_color="#0f172a")
            else:
                btn.configure(fg_color="#27272a", text_color="#e4e4e7")
        self.refresh_installed_slots()

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
            
            # Determine category
            name_lower = (pname + " " + nfile).lower()
            if any(k in name_lower for k in ["petrucci", "timmons", "jp ", "jp2c", "at "]):
                cat_tag = "SIGNATURE"
                tag_bg = "#7e22ce"
            elif any(k in name_lower for k in ["drive", "od", "ts808", "ts9", "boost", "fuzz", "dist", "throttle", "1981", "dude"]):
                cat_tag = "DRIVE"
                tag_bg = "#15803d"
            elif any(k in name_lower for k in ["clean", "jazz", "sss", "cln"]):
                cat_tag = "CLEAN"
                tag_bg = "#0369a1"
            else:
                cat_tag = "AMP"
                tag_bg = "#c2410c"
                
            info['cat_tag'] = cat_tag
            info['tag_bg'] = tag_bg
            
            # Filter by category chip
            if getattr(self, 'selected_category', 'Todos') != 'Todos':
                sel = self.selected_category
                if sel == "Amps" and cat_tag != "AMP": continue
                elif sel == "Drives" and cat_tag != "DRIVE": continue
                elif sel == "Clean" and cat_tag != "CLEAN": continue
                elif sel == "Signature" and cat_tag != "SIGNATURE": continue
            
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
        slot_lbl.pack(side="left", padx=(10, 4), pady=8)

        # Category Tag
        cat_badge = ctk.CTkLabel(
            row,
            text=info.get('cat_tag', 'AMP'),
            font=ctk.CTkFont(size=9, weight="bold"),
            fg_color=info.get('tag_bg', '#c2410c'),
            text_color="#ffffff",
            corner_radius=4,
            width=70,
            height=22
        )
        cat_badge.pack(side="left", padx=4)
        
        # Drive knob value
        drive_lbl = ctk.CTkLabel(
            row,
            text=f"Drive: {info.get('drive', info['slot'])}%",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f59e0b",
            width=75
        )
        drive_lbl.pack(side="left", padx=4)
        
        # Preset Name & File
        center_box = ctk.CTkFrame(row, fg_color="transparent")
        center_box.pack(side="left", fill="x", expand=True, padx=8)
        
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
            width=120
        )
        trims_lbl.pack(side="left", padx=6)
        
        # Actions Box
        actions_box = ctk.CTkFrame(row, fg_color="transparent")
        actions_box.pack(side="right", padx=6)

        btn_inspect = ctk.CTkButton(
            actions_box,
            text="🔍",
            width=32,
            height=28,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=12),
            command=lambda i=info: self.open_inspect_dialog(i)
        )
        btn_inspect.pack(side="left", padx=2)

        btn_bundle = ctk.CTkButton(
            actions_box,
            text="📦",
            width=32,
            height=28,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=12),
            command=lambda i=info: self.export_slot_action(i)
        )
        btn_bundle.pack(side="left", padx=2)
        
        btn_edit = ctk.CTkButton(
            actions_box,
            text="✏️ Trims",
            width=80,
            height=28,
            fg_color="#27272a",
            hover_color="#3f3f46",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda s=info['slot']: self.open_edit_dialog(s)
        )
        btn_edit.pack(side="left", padx=3)

        btn_move = ctk.CTkButton(
            actions_box,
            text="🚚",
            width=36,
            height=28,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=12),
            command=lambda s=info['slot']: self.open_move_dialog(s)
        )
        btn_move.pack(side="left", padx=2)
        
        btn_del = ctk.CTkButton(
            actions_box,
            text="🗑️",
            width=32,
            height=28,
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            command=lambda s=info['slot']: self.confirm_delete_slot(s)
        )
        btn_del.pack(side="left", padx=2)

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
        dialog.geometry("490x540")
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

        def format_for_lcd():
            current = ent_name.get()
            formatted = self.backend.smart_format_preset_name(current)
            ent_name.delete(0, 'end')
            ent_name.insert(0, formatted)

        btn_format_lcd = ctk.CTkButton(
            name_frame,
            text="⚡ Formatar Nome para LCD (Até 24 caracteres)",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            height=24,
            command=format_for_lcd
        )
        btn_format_lcd.pack(anchor="w", pady=(0, 4))
        
        chk_sync_nam = ctk.CTkCheckBox(
            name_frame, 
            text="Sincronizar e renomear arquivo .nam em /NAM",
            font=ctk.CTkFont(size=11),
            text_color="#a1a1aa"
        )
        chk_sync_nam.select()
        chk_sync_nam.pack(anchor="w", pady=(2, 6))

        # Tone Trim Box (Input Gain)
        tone_box = ctk.CTkFrame(dialog, fg_color="#18181b", corner_radius=8)
        tone_box.pack(fill="x", padx=25, pady=4)
        
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
        level_box.pack(fill="x", padx=25, pady=4)
        
        top_level = ctk.CTkFrame(level_box, fg_color="transparent")
        top_level.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(top_level, text="Level Knob (Output Trim / Volume Geral):", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        lbl_level_val = ctk.CTkLabel(top_level, text=f"{info.get('level', 70)}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#10b981")
        lbl_level_val.pack(side="right")
        
        slider_level = ctk.CTkSlider(level_box, from_=0, to=100, number_of_steps=100)
        slider_level.set(info.get('level', 70))
        slider_level.pack(fill="x", padx=10, pady=(4, 8))
        slider_level.configure(command=lambda v: lbl_level_val.configure(text=str(int(v))))

        # Quick Trim Presets
        presets_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        presets_frame.pack(fill="x", padx=25, pady=(2, 6))
        ctk.CTkLabel(presets_frame, text="⚡ Presets Rápidos de Calibração:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8").pack(anchor="w")

        quick_row = ctk.CTkFrame(presets_frame, fg_color="transparent")
        quick_row.pack(fill="x", pady=2)

        def set_trims(t, l):
            slider_tone.set(t)
            lbl_tone_val.configure(text=str(t))
            slider_level.set(l)
            lbl_level_val.configure(text=str(l))

        ctk.CTkButton(quick_row, text="🎸 Clean Boost", width=100, height=24, font=ctk.CTkFont(size=10), fg_color="#1e293b", command=lambda: set_trims(55, 80)).pack(side="left", padx=2)
        ctk.CTkButton(quick_row, text="🔥 Hot Drive", width=100, height=24, font=ctk.CTkFont(size=10), fg_color="#1e293b", command=lambda: set_trims(50, 70)).pack(side="left", padx=2)
        ctk.CTkButton(quick_row, text="⚡ High Gain", width=100, height=24, font=ctk.CTkFont(size=10), fg_color="#1e293b", command=lambda: set_trims(45, 65)).pack(side="left", padx=2)
        ctk.CTkButton(quick_row, text="🎧 Unity", width=90, height=24, font=ctk.CTkFont(size=10), fg_color="#1e293b", command=lambda: set_trims(50, 50)).pack(side="left", padx=2)

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
    # TAB 2: TONE3000 CLOUD EXPLORER (LIVE REST API)
    # ====================================================================
    def setup_catalog_tab(self):
        # Top control bar
        search_frame = ctk.CTkFrame(self.tab_catalog, fg_color="#1e1e24", corner_radius=8)
        search_frame.pack(fill="x", padx=10, pady=8)
        
        # Search entry
        self.ent_search = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Busque timbres na nuvem TONE3000 (ex: Mesa, Klon, 5150, Soldano, Friedman, Bass)...",
            height=36,
            font=ctk.CTkFont(size=13)
        )
        self.ent_search.pack(side="left", fill="x", expand=True, padx=(12, 6), pady=10)
        self.ent_search.bind("<Return>", lambda e: self.do_cloud_search(mode="search"))
        
        # Feed / Mode Selector
        self.opt_mode = ctk.CTkOptionMenu(
            search_frame,
            values=["🔥 Em Alta (Trending)", "✨ Recentes (Latest)", "🔍 Busca Geral"],
            width=170,
            height=36,
            command=self._on_mode_change
        )
        self.opt_mode.pack(side="left", padx=4, pady=10)

        # Gear Filter
        self.opt_category = ctk.CTkOptionMenu(
            search_frame,
            values=["Todos os Tipos", "Cabeçote / Amp", "Pedal", "Amp + Gabinete", "Gabinete / IR"],
            width=140,
            height=36,
            command=lambda v: self.do_cloud_search()
        )
        self.opt_category.pack(side="left", padx=4, pady=10)
        
        # Search Button
        btn_search = ctk.CTkButton(
            search_frame,
            text="Buscar",
            width=90,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=lambda: self.do_cloud_search(mode="search")
        )
        btn_search.pack(side="left", padx=(4, 4), pady=10)

        # API Keys Button
        btn_keys = ctk.CTkButton(
            search_frame,
            text="🔑 Chaves API",
            width=110,
            height=36,
            font=ctk.CTkFont(size=12),
            fg_color="#334155",
            hover_color="#475569",
            command=self.show_api_keys_dialog
        )
        btn_keys.pack(side="left", padx=(4, 12), pady=10)
        
        # Quick Tags Bar
        tags_bar = ctk.CTkFrame(self.tab_catalog, fg_color="transparent")
        tags_bar.pack(fill="x", padx=10, pady=(0, 4))
        
        quick_tags = ["Mesa Boogie", "Marshall", "Soldano", "Friedman", "5150", "Dumble", "Klon", "TS808", "Bogner", "Petrucci", "Bass", "King of Tone"]
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
        
        # Initial search: Load trending models
        self.do_cloud_search(mode="trending")

    def show_api_keys_dialog(self):
        from tone3000_client import get_tone3000_client
        client = get_tone3000_client()

        dlg = ctk.CTkToplevel(self)
        dlg.title("Credenciais TONE3000 API")
        dlg.geometry("520x360")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(
            dlg,
            text="🔑 Configuração Segura TONE3000",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8"
        ).pack(anchor="w", padx=20, pady=(16, 4))

        ctk.CTkLabel(
            dlg,
            text="Suas chaves são salvas APENAS localmente no seu computador\n(~/.headrush_nam_studio/config.json) e NUNCA incluídas no código ou Git.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 12))

        ctk.CTkLabel(dlg, text="Public Key (client_id):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(4, 2))
        ent_pub = ctk.CTkEntry(dlg, height=32, font=ctk.CTkFont(size=12))
        ent_pub.pack(fill="x", padx=20, pady=(0, 8))
        ent_pub.insert(0, client.public_key or "")

        ctk.CTkLabel(dlg, text="Secret Key (t3k_cs_...):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(4, 2))
        ent_sec = ctk.CTkEntry(dlg, height=32, font=ctk.CTkFont(size=12), show="•")
        ent_sec.pack(fill="x", padx=20, pady=(0, 16))
        ent_sec.insert(0, client.secret_key or "")

        def _save():
            p_key = ent_pub.get().strip()
            s_key = ent_sec.get().strip()
            if s_key and not s_key.startswith("t3k_cs_"):
                messagebox.showwarning("Formato Inválido", "A Secret Key do TONE3000 deve começar com 't3k_cs_'")
                return
            client.save_credentials(public_key=p_key, secret_key=s_key)
            dlg.destroy()
            messagebox.showinfo("Salvo com Sucesso", "Suas credenciais foram salvas com segurança no seu computador!")
            self.do_cloud_search(mode="trending")

        btn_save = ctk.CTkButton(
            dlg,
            text="💾 Salvar Credenciais",
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#16a34a",
            hover_color="#15803d",
            command=_save
        )
        btn_save.pack(pady=10)

    def _on_mode_change(self, val):
        if "Trending" in val:
            self.do_cloud_search(mode="trending")
        elif "Recentes" in val or "Latest" in val:
            self.do_cloud_search(mode="latest")
        else:
            self.do_cloud_search(mode="search")

    def quick_search(self, query):
        self.ent_search.delete(0, 'end')
        self.ent_search.insert(0, query)
        self.opt_mode.set("🔍 Busca Geral")
        self.do_cloud_search(mode="search")

    def do_cloud_search(self, mode=None):
        if mode is None:
            val = self.opt_mode.get()
            if "Trending" in val:
                mode = "trending"
            elif "Recentes" in val or "Latest" in val:
                mode = "latest"
            else:
                mode = "search"

        query = self.ent_search.get().strip()
        if mode == "search" and not query:
            query = "Mesa"
            self.ent_search.insert(0, query)

        cat_choice = self.opt_category.get()
        cat_map = {
            "Cabeçote / Amp": "amp",
            "Pedal": "pedal",
            "Amp + Gabinete": "amp-cab",
            "Gabinete / IR": "cab"
        }
        target_gear = cat_map.get(cat_choice)

        for widget in self.catalog_scroll.winfo_children():
            widget.destroy()

        lbl_loading = ctk.CTkLabel(
            self.catalog_scroll,
            text="⏳ Conectando à nuvem TONE3000 e buscando timbres...",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_loading.pack(pady=40)

        threading.Thread(
            target=self._fetch_cloud_tones_thread,
            args=(query, target_gear, mode),
            daemon=True
        ).start()

    def _fetch_cloud_tones_thread(self, query, gear, mode):
        try:
            if mode == "trending":
                tones = self.backend.cloud_trending(gear=gear)
                title = "🔥 Timbres em Alta no TONE3000 (Mais Populares):"
            elif mode == "latest":
                tones = self.backend.cloud_latest(gear=gear)
                title = "✨ Últimos Timbres Publicados pela Comunidade:"
            else:
                res = self.backend.cloud_search(query=query, gear=gear, page=1)
                tones = res.get("tones", [])
                total = res.get("total", len(tones))
                title = f"🔍 Encontrados {total} resultados para '{query}':"
            
            self.after(0, lambda: self._render_cloud_tones(tones, title))
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda: self._render_cloud_error(err_msg))

    def _render_cloud_error(self, err_msg):
        for widget in self.catalog_scroll.winfo_children():
            widget.destroy()
            
        ctk.CTkLabel(
            self.catalog_scroll,
            text=f"⚠️ Erro ao consultar a API TONE3000:\n{err_msg}\n\nVerifique sua conexão com a internet.",
            font=ctk.CTkFont(size=13),
            text_color="#ef4444"
        ).pack(pady=40)

    def _render_cloud_tones(self, tones, title_text):
        for widget in self.catalog_scroll.winfo_children():
            widget.destroy()

        if not tones:
            ctk.CTkLabel(
                self.catalog_scroll,
                text="Nenhum timbre encontrado para os filtros selecionados.\nTente outra busca ou selecione 'Em Alta'.",
                font=ctk.CTkFont(size=14),
                text_color="#71717a"
            ).pack(pady=40)
            return

        summary_lbl = ctk.CTkLabel(
            self.catalog_scroll,
            text=f"{title_text} ({len(tones)} exibidos)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8",
            anchor="w"
        )
        summary_lbl.pack(fill="x", padx=8, pady=4)

        installed_slots = self.backend.get_installed_slots()
        installed_names = {info.get('preset_name', '').lower(): s for s, info in installed_slots.items()}

        for t in tones:
            self.create_cloud_tone_card(t, installed_names)

    def create_cloud_tone_card(self, tone_obj, installed_names):
        card = ctk.CTkFrame(self.catalog_scroll, fg_color="#18181b", corner_radius=8)
        card.pack(fill="x", pady=4, padx=4)

        # Gear tag
        gear = tone_obj.get("gear", "amp")
        gear_color = "#3b82f6" if gear in ["amp", "amp-cab"] else "#8b5cf6"
        gear_label = {"amp": "AMP", "pedal": "PEDAL", "amp-cab": "RIG", "cab": "CAB/IR"}.get(gear, gear.upper())
        
        gear_badge = ctk.CTkLabel(
            card,
            text=gear_label,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=gear_color,
            text_color="#ffffff",
            corner_radius=4,
            width=64,
            height=22
        )
        gear_badge.pack(side="left", padx=10, pady=10)

        # Info Box
        info_box = ctk.CTkFrame(card, fg_color="transparent")
        info_box.pack(side="left", fill="x", expand=True, padx=8)

        title_box = ctk.CTkFrame(info_box, fg_color="transparent")
        title_box.pack(anchor="w")

        title_text = tone_obj.get("title") or tone_obj.get("name") or "Sem Título"
        title_lbl = ctk.CTkLabel(
            title_box,
            text=title_text[:40],
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff"
        )
        title_lbl.pack(side="left")

        # Author and metrics
        creator = (tone_obj.get("user") or {}).get("username") or "Comunidade"
        likes = tone_obj.get("favorites_count", 0)
        dls = tone_obj.get("downloads_count", 0)
        models_count = tone_obj.get("models_count", 1)

        desc_lbl = ctk.CTkLabel(
            info_box,
            text=f"Por: {creator}  ·  ❤️ {likes} likes  ·  ⬇️ {dls} downloads  ·  📦 {models_count} captura(s)",
            font=ctk.CTkFont(size=11),
            text_color="#a1a1aa",
            anchor="w"
        )
        desc_lbl.pack(anchor="w")

        # Action Buttons
        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.pack(side="right", padx=12, pady=10)

        tone_id = tone_obj.get("id")
        btn_inspect = ctk.CTkButton(
            btn_box,
            text=f"⚡ Ver Capturas ({models_count})",
            width=150,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=lambda tid=tone_id, tobj=tone_obj: self.show_tone_models_dialog(tid, tobj)
        )
        btn_inspect.pack(side="left", padx=2)

    def show_tone_models_dialog(self, tone_id, tone_obj):
        """Displays modal with all captures/models inside a tone for selective installation."""
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Capturas NAM · {tone_obj.get('title', '')[:30]}")
        dlg.geometry("640x480")
        dlg.transient(self)
        dlg.grab_set()

        top_f = ctk.CTkFrame(dlg, fg_color="#1e1e24", corner_radius=0)
        top_f.pack(fill="x", padx=0, pady=0)
        ctk.CTkLabel(
            top_f,
            text=f"📦 {tone_obj.get('title', 'Pacote')}",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#38bdf8"
        ).pack(anchor="w", padx=16, pady=(12, 4))
        
        desc = (tone_obj.get("description") or "").replace("\n", " ")[:120]
        if desc:
            ctk.CTkLabel(top_f, text=desc, font=ctk.CTkFont(size=11), text_color="#94a3b8", wraplength=600).pack(anchor="w", padx=16, pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(dlg, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=12, pady=10)

        lbl_loading = ctk.CTkLabel(scroll, text="Carregando modelos do servidor...", font=ctk.CTkFont(size=13), text_color="#38bdf8")
        lbl_loading.pack(pady=20)

        def _fetch():
            try:
                models = self.backend.cloud_models(tone_id)
                self.after(0, lambda: _render(models))
            except Exception as e:
                self.after(0, lambda: lbl_loading.configure(text=f"Erro ao carregar modelos: {e}", text_color="#ef4444"))

        def _render(models):
            lbl_loading.destroy()
            if not models:
                ctk.CTkLabel(scroll, text="Nenhum arquivo NAM disponível para este pacote.", text_color="#94a3b8").pack(pady=20)
                return

            for m in models:
                row = ctk.CTkFrame(scroll, fg_color="#1e1e24", corner_radius=6)
                row.pack(fill="x", pady=3, padx=2)

                m_name = m.get("name", "Modelo NAM")
                size = m.get("size", "Standard")
                
                info = ctk.CTkFrame(row, fg_color="transparent")
                info.pack(side="left", fill="x", expand=True, padx=10, pady=8)
                
                ctk.CTkLabel(info, text=m_name, font=ctk.CTkFont(size=13, weight="bold"), text_color="#ffffff").pack(anchor="w")
                ctk.CTkLabel(info, text=f"Tamanho/Arquitetura: {size}", font=ctk.CTkFont(size=10), text_color="#94a3b8").pack(anchor="w")

                btn_inst = ctk.CTkButton(
                    row,
                    text="⚡ Instalar no MX5",
                    width=130,
                    height=28,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color="#16a34a",
                    hover_color="#15803d",
                    command=lambda mobj=m, dlg_ref=dlg: self._install_cloud_model(mobj, dlg_ref)
                )
                btn_inst.pack(side="right", padx=10, pady=8)

        threading.Thread(target=_fetch, daemon=True).start()

    def _install_cloud_model(self, model_obj, dlg_ref=None):
        if not self.backend.is_connected():
            messagebox.showerror("HeadRush Desconectada", "Conecte sua HeadRush MX5 via USB em modo de transferência para instalar.")
            return

        next_slot = self.backend.get_next_free_slot()
        if next_slot is None:
            messagebox.showwarning("Pedaleira Cheia", "Todos os 101 slots (000-100) da sua HeadRush estão ocupados! Exclua algum timbre antes.")
            return

        m_name = model_obj.get("name", "Cloud Tone")
        
        # Prompt slot/trim adjustment or install directly
        res_confirm = messagebox.askyesno(
            "Instalar Timbre da Nuvem",
            f"Deseja baixar e instalar '{m_name}' no Slot {next_slot:03d} da sua HeadRush MX5?\n\n"
            f"• Nome no Display: {self.backend.smart_format_preset_name(m_name, 24)}\n"
            f"• Bloco ANXIETY OD V2 sincronizado automaticamente."
        )
        if not res_confirm:
            return

        if dlg_ref:
            dlg_ref.destroy()

        # Run background installation
        prog_win = ctk.CTkToplevel(self)
        prog_win.title("Baixando e Instalando...")
        prog_win.geometry("380x140")
        prog_win.transient(self)
        prog_win.grab_set()

        lbl_status = ctk.CTkLabel(prog_win, text=f"Baixando '{m_name}'\nda nuvem TONE3000...", font=ctk.CTkFont(size=13))
        lbl_status.pack(pady=(20, 10))
        prog_bar = ctk.CTkProgressBar(prog_win, mode="indeterminate", width=280)
        prog_bar.pack(pady=5)
        prog_bar.start()

        def _worker():
            try:
                res = self.backend.cloud_install(
                    model_obj=model_obj,
                    slot=next_slot,
                    custom_name=m_name,
                    tone=50,
                    level=70
                )
                self.after(0, lambda: _on_success(res, prog_win))
            except Exception as e:
                err_str = str(e)
                self.after(0, lambda: _on_error(err_str, prog_win))

        def _on_success(res, win):
            win.destroy()
            self.refresh_installed_slots()
            messagebox.showinfo(
                "Instalação Concluída! 🚀",
                f"Timbre baixado e instalado com sucesso!\n\n"
                f"• Slot HeadRush: {res['slot']:03d}\n"
                f"• Nome no LCD: {res['preset_name']}\n"
                f"• Bloco V1 e V2 criados com sucesso!\n\n"
                f"Lembre-se de reiniciar sua MX5 para que ela recarregue os novos blocos."
            )

        def _on_error(err_str, win):
            win.destroy()
            messagebox.showerror("Falha no Download/Instalação", f"Não foi possível instalar o modelo da nuvem:\n{err_str}")

        threading.Thread(target=_worker, daemon=True).start()

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

---

### ☕ 5. Projeto Gratuito & Apoio ao Desenvolvedor
- O **HeadRush NAM Studio Pro** é e sempre será **100% gratuito e livre**.
- O projeto está em desenvolvimento ativo com novas atualizações e melhorias frequentes.
- Se o programa é útil para você, considere pagar um café para incentivar e manter o projeto vivo!
"""
        lbl = ctk.CTkLabel(
            frame,
            text=help_text,
            justify="left",
            font=ctk.CTkFont(size=13),
            text_color="#d4d4d8"
        )
        lbl.pack(anchor="w", padx=10, pady=10)

        # Help Tab Donation Banner
        donate_card = ctk.CTkFrame(frame, fg_color="#1e1e24", corner_radius=8, border_width=1, border_color="#d97706")
        donate_card.pack(fill="x", padx=10, pady=16)

        ctk.CTkLabel(
            donate_card,
            text="☕ Gostou da ferramenta? Pague um café para o desenvolvedor!",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f59e0b"
        ).pack(anchor="w", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            donate_card,
            text="Sua contribuição ajuda a cobrir os custos e o tempo dedicado a criar novos recursos para a comunidade.",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        ).pack(anchor="w", padx=16, pady=(0, 10))

        ctk.CTkButton(
            donate_card,
            text="☕ Apoiar Agora / Chave PIX",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#d97706",
            hover_color="#b45309",
            command=self.show_donation_dialog
        ).pack(anchor="w", padx=16, pady=(0, 12))

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

    # ====================================================================
    # PRO SUITE: BATCH IMPORT, CHEAT SHEET, HEALTH, DUPLICATES, SETLISTS
    # ====================================================================
    def open_batch_import_dialog(self):
        if not self.backend.is_connected():
            messagebox.showerror("Erro", "Pedaleira HeadRush MX5 não conectada.")
            return
            
        dialog = ctk.CTkToplevel(self)
        dialog.title("📂 Importação em Lote · HeadRush NAM Studio")
        dialog.geometry("540x520")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(
            dialog,
            text="📂 Importar Pacote de Modelos (.nam) do PC",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#10b981"
        ).pack(pady=(16, 4))
        
        ctk.CTkLabel(
            dialog,
            text="Selecione múltiplos arquivos .nam ou uma pasta inteira de timbres.",
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa"
        ).pack(pady=(0, 10))
        
        selected_files = []
        
        files_box = ctk.CTkTextbox(dialog, height=180, font=ctk.CTkFont(size=11))
        files_box.pack(fill="x", padx=20, pady=6)
        files_box.insert("1.0", "Nenhum arquivo selecionado ainda...")
        files_box.configure(state="disabled")
        
        lbl_count = ctk.CTkLabel(dialog, text="0 arquivos .nam selecionados", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_count.pack(pady=2)

        def pick_files():
            nonlocal selected_files
            paths = filedialog.askopenfilenames(
                title="Selecione os arquivos .nam",
                filetypes=[("Neural Amp Models", "*.nam"), ("Todos os Arquivos", "*.*")]
            )
            if paths:
                selected_files = list(paths)
                update_list()

        def pick_folder():
            nonlocal selected_files
            folder = filedialog.askdirectory(title="Selecione uma pasta com arquivos .nam")
            if folder:
                found = []
                for root, _, f_list in os.walk(folder):
                    for f in f_list:
                        if f.lower().endswith('.nam'):
                            found.append(os.path.join(root, f))
                selected_files = sorted(found)
                update_list()

        def update_list():
            files_box.configure(state="normal")
            files_box.delete("1.0", "end")
            for f in selected_files:
                files_box.insert("end", f"{os.path.basename(f)}\n")
            files_box.configure(state="disabled")
            lbl_count.configure(text=f"{len(selected_files)} arquivos .nam encontrados")

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=4)
        ctk.CTkButton(btn_row, text="📄 Escolher Arquivos", command=pick_files, fg_color="#334155").pack(side="left", expand=True, fill="x", padx=2)
        ctk.CTkButton(btn_row, text="📁 Escolher Pasta", command=pick_folder, fg_color="#334155").pack(side="left", expand=True, fill="x", padx=2)

        chk_smart = ctk.CTkCheckBox(dialog, text="⚡ Otimizar e encurtar nomes automaticamente para o visor da MX5", font=ctk.CTkFont(size=11))
        chk_smart.select()
        chk_smart.pack(anchor="w", padx=24, pady=6)

        def do_import():
            if not selected_files:
                messagebox.showwarning("Aviso", "Selecione ao menos um arquivo .nam!")
                return
            dialog.destroy()
            try:
                res = self.backend.import_local_models_batch(selected_files, smart_rename=bool(chk_smart.get()))
                self.refresh_installed_slots()
                msg = f"Importação Concluída com Sucesso! 🚀\n\n" \
                      f"• {res['count']} modelos instalados em slots consecutivos na HeadRush.\n"
                if res['skipped']:
                    msg += f"• {len(res['skipped'])} arquivos ignorados (ex: limite de 101 slots).\n"
                msg += "\n⚠️ Lembre-se de reiniciar sua HeadRush MX5 para que ela reconheça os novos blocos!"
                messagebox.showinfo("Sucesso!", msg)
            except Exception as e:
                messagebox.showerror("Erro ao Importar", str(e))

        ctk.CTkButton(
            dialog,
            text="⚡ Instalar Todos na HeadRush MX5",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            height=38,
            command=do_import
        ).pack(fill="x", padx=20, pady=(10, 16))

    def open_cheatsheet_dialog(self):
        slots = self.backend.get_installed_slots()
        occupied = [info for s, info in sorted(slots.items()) if info.get('nam_file')]
        if not occupied:
            messagebox.showinfo("Guia de Palco", "Nenhum modelo instalado ainda na pedaleira.")
            return
            
        dialog = ctk.CTkToplevel(self)
        dialog.title("📋 Guia de Palco (Stage Cheat Sheet)")
        dialog.geometry("620x520")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="📋 Guia de Palco (Stage Cheat Sheet)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8"
        ).pack(pady=(16, 4))
        
        txt_content = self.backend.generate_stage_cheat_sheet("txt")
        
        box = ctk.CTkTextbox(dialog, font=ctk.CTkFont(family="Courier", size=11))
        box.pack(fill="both", expand=True, padx=20, pady=8)
        box.insert("1.0", txt_content)
        box.configure(state="disabled")
        
        btn_bar = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_bar.pack(fill="x", padx=20, pady=(4, 16))
        
        def save_file(fmt, ext):
            p = filedialog.asksaveasfilename(
                title=f"Salvar Guia de Palco ({fmt.upper()})",
                defaultextension=ext,
                filetypes=[(f"Arquivo {fmt.upper()}", f"*{ext}")]
            )
            if p:
                content = self.backend.generate_stage_cheat_sheet(fmt)
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Salvo", f"Guia de palco salvo em:\n{p}")

        def open_browser():
            import tempfile, webbrowser
            html = self.backend.generate_stage_cheat_sheet("html")
            tmp = os.path.join(tempfile.gettempdir(), "headrush_stage_cheatsheet.html")
            with open(tmp, 'w', encoding='utf-8') as f:
                f.write(html)
            webbrowser.open(f"file:///{tmp.replace(os.sep, '/')}")

        ctk.CTkButton(btn_bar, text="🌐 Abrir p/ Imprimir (HTML)", command=open_browser, fg_color="#0284c7").pack(side="left", padx=3, expand=True, fill="x")
        ctk.CTkButton(btn_bar, text="💾 Salvar TXT", command=lambda: save_file("txt", ".txt"), fg_color="#334155").pack(side="left", padx=3, expand=True, fill="x")
        ctk.CTkButton(btn_bar, text="📄 Salvar Markdown", command=lambda: save_file("md", ".md"), fg_color="#334155").pack(side="left", padx=3, expand=True, fill="x")

    def open_health_dialog(self):
        diag = self.backend.perform_health_check()
        dialog = ctk.CTkToplevel(self)
        dialog.title("❤️ Diagnóstico e Saúde da Pedaleira")
        dialog.geometry("520x440")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="❤️ Diagnóstico e Integridade da HeadRush",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#ec4899"
        ).pack(pady=(16, 4))
        
        score = diag.get("score", 0)
        score_color = "#10b981" if score >= 90 else ("#f59e0b" if score >= 70 else "#ef4444")
        
        score_lbl = ctk.CTkLabel(
            dialog,
            text=f"{score}% SAUDÁVEL",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=score_color
        )
        score_lbl.pack(pady=4)

        box = ctk.CTkTextbox(dialog, height=180, font=ctk.CTkFont(size=12))
        box.pack(fill="x", padx=20, pady=8)
        
        report = f"Resumo: {diag.get('summary', '')}\n"
        report += f"Total de Modelos Instalados: {diag.get('total_models', 0)}\n\n"
        if diag.get("issues"):
            report += "❌ PROBLEMAS CRÍTICOS:\n"
            for iss in diag["issues"]:
                report += f"  • {iss}\n"
            report += "\n"
        else:
            report += "✓ Nenhum arquivo corrompido encontrado.\n\n"
            
        if diag.get("warnings"):
            report += "⚠️ AVISOS / ATENÇÃO:\n"
            for w in diag["warnings"]:
                report += f"  • {w}\n"
        else:
            report += "✓ Todos os arquivos .block V1 e V2 estão perfeitamente sincronizados!\n"
            
        box.insert("1.0", report)
        box.configure(state="disabled")

        def auto_repair():
            c1 = self.backend.sync_missing_blocks()
            d1 = self.backend.clean_orphaned_blocks()
            dialog.destroy()
            self.refresh_installed_slots()
            messagebox.showinfo(
                "Reparação Concluída",
                f"Diagnóstico corrigido com sucesso!\n\n"
                f"• {c1} blocos faltantes gerados.\n"
                f"• {len(d1)} blocos órfãos removidos."
            )

        ctk.CTkButton(
            dialog,
            text="🛠️ Reparar Tudo Automaticamente",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=36,
            command=auto_repair
        ).pack(fill="x", padx=20, pady=(6, 16))

    def open_duplicates_dialog(self):
        dups = self.backend.detect_duplicate_models()
        dialog = ctk.CTkToplevel(self)
        dialog.title("🔍 Detector de Modelos Duplicados")
        dialog.geometry("520x400")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="🔍 Detector de Modelos Duplicados",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f59e0b"
        ).pack(pady=(16, 4))

        box = ctk.CTkTextbox(dialog, font=ctk.CTkFont(size=12))
        box.pack(fill="both", expand=True, padx=20, pady=8)
        
        report = ""
        hash_dups = dups.get("hash_duplicates", {})
        if hash_dups:
            report += f"⚠️ {len(hash_dups)} CONTEÚDOS IDÊNTICOS ENCONTRADOS (Mesmo modelo em slots diferentes):\n\n"
            for h, items in hash_dups.items():
                slots_str = ", ".join(f"Slot {it['slot']:03d} ({it['preset_name']})" for it in items)
                report += f"• Arquivo idêntico presente em: {slots_str}\n"
            report += "\n"
        else:
            report += "✓ Nenhum modelo idêntico duplicado por hash de arquivo.\n\n"

        name_dups = dups.get("name_duplicates", {})
        if name_dups:
            report += f"⚠️ {len(name_dups)} NOMES DUPLICADOS ENCONTRADOS:\n"
            for n, s_list in name_dups.items():
                report += f"• Nome '{n}' repetido nos Slots: {', '.join(f'{s:03d}' for s in s_list)}\n"
        else:
            report += "✓ Nenhum nome de preset duplicado.\n"

        box.insert("1.0", report)
        box.configure(state="disabled")

        ctk.CTkButton(
            dialog,
            text="Fechar",
            fg_color="#27272a",
            hover_color="#3f3f46",
            height=32,
            command=dialog.destroy
        ).pack(fill="x", padx=20, pady=(4, 16))

    def open_inspect_dialog(self, info):
        fname = info.get('nam_file')
        if not fname:
            messagebox.showinfo("Aviso", "Este slot não possui arquivo .nam associado.")
            return
            
        full_path = os.path.join(self.backend.nam_dir, fname)
        meta = self.backend.inspect_nam_file(full_path)
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"🔍 Inspecionar Modelo · Slot {info['slot']:03d}")
        dialog.geometry("480x420")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=f"🔍 Detalhes Técnicos · Slot {info['slot']:03d}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8"
        ).pack(pady=(16, 4))
        
        ctk.CTkLabel(
            dialog,
            text=info.get('preset_name') or fname,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff"
        ).pack(pady=(0, 10))

        content_frame = ctk.CTkFrame(dialog, fg_color="#18181b", corner_radius=8)
        content_frame.pack(fill="both", expand=True, padx=20, pady=8)
        
        fields = [
            ("Arquivo:", meta.get("filename", fname)),
            ("Arquitetura:", meta.get("architecture", "WaveNet")),
            ("Taxa de Amostragem:", f"{meta.get('sample_rate', 48000)} Hz"),
            ("Tamanho do Arquivo:", f"{meta.get('size_kb', 0)} KB"),
            ("Criador / Autor:", meta.get("author", "Comunidade")),
            ("Data de Criação:", meta.get("date", "N/A")),
            ("Perda de Treinamento (ESR):", f"{meta.get('training_loss', 'N/A')}")
        ]
        
        for k, v in fields:
            row = ctk.CTkFrame(content_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(row, text=k, font=ctk.CTkFont(size=12, weight="bold"), text_color="#94a3b8", width=170, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=str(v), font=ctk.CTkFont(size=12), text_color="#f8fafc", anchor="w").pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            dialog,
            text="Fechar",
            fg_color="#334155",
            hover_color="#475569",
            height=32,
            command=dialog.destroy
        ).pack(fill="x", padx=20, pady=(6, 16))

    def export_slot_action(self, info):
        pname = self.backend.sanitize_preset_name(info.get('preset_name') or "Model", 20)
        default_filename = f"Slot_{info['slot']:03d}_{pname}.zip"
        dest_zip = filedialog.asksaveasfilename(
            title="Exportar Pacote do Timbre (.zip)",
            initialfile=default_filename,
            defaultextension=".zip",
            filetypes=[("Arquivo ZIP", "*.zip")]
        )
        if dest_zip:
            try:
                self.backend.export_slot_bundle(info['slot'], dest_zip)
                messagebox.showinfo("Exportado com Sucesso! 📦", f"O timbre do Slot {info['slot']:03d} foi empacotado em:\n\n{dest_zip}")
            except Exception as e:
                messagebox.showerror("Erro ao Exportar", str(e))

    # ====================================================================
    # TAB: SETLISTS & PROFILES
    # ====================================================================
    def setup_setlists_tab(self):
        top_bar = ctk.CTkFrame(self.tab_setlists, fg_color="#1e1e24", corner_radius=8)
        top_bar.pack(fill="x", padx=10, pady=8)
        
        ctk.CTkLabel(
            top_bar,
            text="🗂️ Gerenciador de Setlists e Cenários da Pedaleira",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#a855f7"
        ).pack(side="left", padx=16, pady=10)

        btn_save = ctk.CTkButton(
            top_bar,
            text="💾 Salvar Configuração Atual",
            width=180,
            height=30,
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.save_current_setlist_dialog
        )
        btn_save.pack(side="right", padx=6, pady=10)

        btn_import_pack = ctk.CTkButton(
            top_bar,
            text="📥 Importar Setlist (.zip)",
            width=160,
            height=30,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=12),
            command=self.import_setlist_dialog
        )
        btn_import_pack.pack(side="right", padx=6, pady=10)

        self.setlists_scroll = ctk.CTkScrollableFrame(self.tab_setlists, fg_color="transparent")
        self.setlists_scroll.pack(fill="both", expand=True, padx=6, pady=6)

    def refresh_setlists_list(self):
        if not hasattr(self, 'setlists_scroll'):
            return
        for widget in self.setlists_scroll.winfo_children():
            widget.destroy()
            
        lists = self.backend.list_setlists()
        if not lists:
            ctk.CTkLabel(
                self.setlists_scroll,
                text="Nenhum Setlist salvo ainda.\nClique em '💾 Salvar Configuração Atual' para salvar um snapshot da sua pedaleira (ex: 'Show Metal', 'Igreja', 'Estúdio')!",
                font=ctk.CTkFont(size=14),
                text_color="#71717a"
            ).pack(pady=60)
            return

        for s in lists:
            card = ctk.CTkFrame(self.setlists_scroll, fg_color="#18181b", corner_radius=8)
            card.pack(fill="x", pady=4, padx=4)
            
            ctk.CTkLabel(
                card,
                text=f"🗂️ {s['name']}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#ffffff"
            ).pack(side="left", padx=16, pady=12)
            
            ctk.CTkLabel(
                card,
                text=f"({s['total_slots']} timbres salvos) · {s['created_at'][:10]}",
                font=ctk.CTkFont(size=12),
                text_color="#a1a1aa"
            ).pack(side="left", padx=8)

            btn_load = ctk.CTkButton(
                card,
                text="⚡ Carregar na MX5",
                width=130,
                height=28,
                fg_color="#0284c7",
                hover_color="#0369a1",
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda name=s['name']: self.load_setlist_action(name)
            )
            btn_load.pack(side="right", padx=8)

            btn_exp = ctk.CTkButton(
                card,
                text="📦 Exportar",
                width=80,
                height=28,
                fg_color="#334155",
                hover_color="#475569",
                font=ctk.CTkFont(size=11),
                command=lambda name=s['name']: self.export_setlist_action(name)
            )
            btn_exp.pack(side="right", padx=4)

    def save_current_setlist_dialog(self):
        if not self.backend.is_connected():
            messagebox.showerror("Erro", "Pedaleira não conectada.")
            return
            
        dialog = ctk.CTkInputDialog(text="Digite um nome para o Setlist (ex: Show_Rock, Worship, Studio):", title="Salvar Setlist")
        name = dialog.get_input()
        if name and name.strip():
            try:
                self.backend.save_setlist(name.strip())
                self.refresh_setlists_list()
                messagebox.showinfo("Sucesso!", f"Setlist '{name.strip()}' salvo com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", str(e))

    def load_setlist_action(self, name):
        ans = messagebox.askyesno(
            "Confirmar Troca de Setlist",
            f"Deseja realmente carregar o Setlist '{name}' na sua HeadRush MX5?\n\n"
            f"• Um backup de segurança da sua pedaleira atual será criado automaticamente antes de aplicar."
        )
        if not ans:
            return
        try:
            res = self.backend.load_setlist(name)
            self.refresh_all()
            messagebox.showinfo(
                "Setlist Carregado! 🚀",
                f"Setlist '{name}' aplicado com sucesso na sua pedaleira!\n\n"
                f"⚠️ Reinicie sua HeadRush MX5 para que ela reconheça a nova lista de timbres."
            )
        except Exception as e:
            messagebox.showerror("Erro ao Carregar Setlist", str(e))

    def export_setlist_action(self, name):
        dest_zip = filedialog.asksaveasfilename(
            title=f"Exportar Setlist '{name}'",
            initialfile=f"Setlist_{name}.hrpack",
            defaultextension=".hrpack",
            filetypes=[("HeadRush Pack", "*.hrpack"), ("Arquivo ZIP", "*.zip")]
        )
        if dest_zip:
            try:
                self.backend.export_setlist_zip(name, dest_zip)
                messagebox.showinfo("Sucesso!", f"Setlist exportado com sucesso em:\n\n{dest_zip}")
            except Exception as e:
                messagebox.showerror("Erro ao Exportar", str(e))

    def import_setlist_dialog(self):
        src_zip = filedialog.askopenfilename(
            title="Importar Setlist (.hrpack / .zip)",
            filetypes=[("HeadRush Pack / ZIP", "*.hrpack;*.zip"), ("Todos os Arquivos", "*.*")]
        )
        if src_zip:
            try:
                dest = self.backend.import_setlist_zip(src_zip)
                self.refresh_setlists_list()
                messagebox.showinfo("Sucesso!", f"Setlist importado com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro ao Importar", str(e))

def main():
    app = HeadRushApp()
    app.mainloop()

if __name__ == "__main__":
    main()
