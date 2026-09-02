# 🎸 HeadRush NAM Studio Pro

[![Tests & Linting](https://github.com/tiagojsoares/headrush-nam-studio/actions/workflows/test.yml/badge.svg)](https://github.com/tiagojsoares/headrush-nam-studio/actions/workflows/test.yml)
[![Build & Release](https://github.com/tiagojsoares/headrush-nam-studio/actions/workflows/release.yml/badge.svg)](https://github.com/tiagojsoares/headrush-nam-studio/actions/workflows/release.yml)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![UI Framework](https://img.shields.io/badge/UI-CustomTkinter-blueviolet.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Target Device](https://img.shields.io/badge/hardware-HeadRush%20MX5%20%7C%20Prime%20%7C%20Core%20%7C%20Gigboard-orange.svg)]()

**HeadRush NAM Studio Pro** is a modern, ultra-resilient desktop management suite and sound librarian designed for **HeadRush multi-effects processors** (MX5, Prime, Core, Gigboard, Pedalboard) running the [headrush-nam-mod](https://github.com/headrush-nam-mod) Neural Amp Modeler firmware.

---

## 🇧🇷 Português

### ✨ Recursos Principais
- 🎛️ **Gerenciador Visual de Slots (000 a 100)**: Visualização em tempo real de todos os 101 slots da pedaleira, com edição gráfica de trims de ganho (*Tone*) e volume (*Level*).
- 🔍 **Catálogo Tone3000 Integrado (97k+ Timbres)**: Motor de busca instantâneo (< 1ms com SQLite FTS5) sobre a biblioteca local completa com filtros rápidos para `5150`, `Dumble`, `Petrucci`, `Andy Timmons`, `1981 DRV`, `Mesa Mark`, `Bogner`, etc.
- ⚡ **Instalação com 1-Clique**: Localiza automaticamente o próximo slot livre, copia o modelo `.nam` e gera instantaneamente o bloco de preset `.block`.
- 🛡️ **Compatibilidade Dupla Blindada**: Gera presets simultaneamente para `Anxiety OD` (v1) e `Anxiety OD V2` (até 4 instâncias), funcionando em qualquer versão do mod.
- 🔊 **Gerenciador de Impulse Responses (IRs)**: Navega por pastas de IRs na pedaleira e cria blocos de gabinete prontos para uso com ganho ajustável em dB.
- 💾 **Snapshots e Backup com 1-Clique**: Salve cópias de segurança instantâneas de todos os seus modelos e blocos de preset com timestamp.

### 🚀 Como Usar o Executável (.exe)
1. Conecte sua HeadRush ao PC via USB e entre em **USB Transfer** (Menu 3 Pontos -> USB Transfer).
2. Abra o **HeadRush NAM Studio**.
3. Na aba **Catálogo**, busque o som desejado e clique em **⚡ Enviar p/ MX5**.
4. **Desconecte o cabo USB e REINICIE a pedaleira** (a HeadRush só carrega novos arquivos NAM durante o boot!).
5. No seu Rig, adicione o pedal **Anxiety OD V2** e selecione o preset criado!

---

## 🇺🇸 English

### ✨ Key Features
- 🎛️ **Visual Slot Manager (000 to 100)**: Real-time overview of all 101 slots on your HeadRush, with graphical sliders for Input Trim (*Tone*) and Output Trim (*Level*).
- 🔍 **Integrated Tone3000 Library (97k+ Models)**: Blazing-fast (<1ms SQLite FTS5) search engine with instant chips for popular amps, drives, and signature tones.
- ⚡ **1-Click Model Installer**: Auto-allocates the next available slot, copies the `.nam` file to `/NAM`, and generates the corresponding `.block` preset file.
- 🛡️ **Dual-Compatibility Presets**: Auto-generates block files for both `Anxiety OD` and `Anxiety OD V2` pedal hijacks.
- 🔊 **Impulse Response Manager**: Browse onboard IR folders and generate ready-to-use cabinet `.block` presets with adjustable gain.
- 💾 **1-Click Full Backup**: Create timestamped backup snapshots of all NAM files and block presets before making changes.

---

## 🛠️ Installation & Running from Source

### Prerequisites
- Python 3.10 or newer

```bash
# Clone the repository
git clone https://github.com/your-username/headrush-nam-studio.git
cd headrush-nam-studio

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Launch GUI Application
python main.py

# Or launch CLI mode
python main.py --cli list
```

---

## 📦 Building the Standalone .exe (Windows)

You can compile a standalone, single-file Windows executable (`HeadRush_NAM_Studio.exe`) without requiring Python installed on target machines:

### Option A: 1-Click Batch File
Double-click `build_exe.bat` in the repository root.

### Option B: Command Line
```bash
python scripts/build_executable.py
```
The compiled executable will be placed in the `dist/` directory.

---

## 📂 Project Structure

```
headrush-nam-studio/
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
├── main.py                     # Main application entry point
├── build_exe.bat               # 1-Click build script for Windows
├── src/
│   ├── __init__.py
│   ├── app_gui.py              # CustomTkinter Dark Modern GUI
│   ├── headrush_manager.py     # Hardware bridge & slot manager
│   └── headrush_cli.py         # Command Line Interface (CLI)
├── scripts/
│   └── build_executable.py     # PyInstaller automation script
└── docs/
    ├── HARDWARE_GUIDE.md       # HeadRush USB & NAM mod instructions
    └── ARCHITECTURE.md         # JSON block schemas & reverse engineering
```

---

## 🤝 Contributing & License
Contributions, bug reports, and feature requests are welcome!
Licensed under the [MIT License](LICENSE).
