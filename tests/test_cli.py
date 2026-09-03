import os
import sys
import pytest
import headrush_cli as cli
import headrush_manager as hm

def test_cli_help_and_subcommands(capsys):
    """Tests CLI argument parsing and help output."""
    sys.argv = ["headrush_cli.py", "--help"]
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "HeadRush MX5 NAM & IR Manager Pro" in captured.out
    for sub in ["list", "install", "batch", "organize", "cheatsheet", "duplicates", "inspect", "health", "storage", "eject", "setlist"]:
        assert sub in captured.out

def test_cli_list_command(mock_pedal_drive, capsys):
    """Tests listing slots on empty and populated pedalboards."""
    # 1. Empty pedalboard
    sys.argv = ["headrush_cli.py", "list"]
    cli.main()
    captured = capsys.readouterr()
    assert "INSTALLED NAM MODELS & BLOCK PRESETS" in captured.out
    assert "Total slots occupied: 0 / 101" in captured.out

    # 2. Add a model and test list formatting
    hm.create_block_preset(0, "MESA LEAD", 50, 70)
    sys.argv = ["headrush_cli.py", "list"]
    cli.main()
    captured = capsys.readouterr()
    assert "Total slots occupied: 1 / 101" in captured.out
    assert "000" in captured.out
    assert "MESA LEAD" in captured.out

def test_cli_install_and_inspect_commands(mock_pedal_drive, realistic_nam_files, capsys):
    """Tests installing a model via CLI arguments and inspecting its metadata."""
    src_file = realistic_nam_files["wavenet"]
    sys.argv = [
        "headrush_cli.py",
        "install",
        src_file,
        "--slot", "8",
        "--name", "CUSTOM RIG",
        "--tone", "44",
        "--level", "82"
    ]
    cli.main()
    captured = capsys.readouterr()
    assert "Successfully installed to slot 008" in captured.out
    assert "Tone=44" in captured.out and "Level=82" in captured.out
    
    # Inspect the installed file
    installed_path = os.path.join(hm.get_nam_dir(), "008 - CUSTOM RIG.nam")
    assert os.path.exists(installed_path)
    
    sys.argv = ["headrush_cli.py", "inspect", installed_path]
    cli.main()
    captured = capsys.readouterr()
    assert "NAM MODEL INSPECTOR" in captured.out
    assert "WaveNet" in captured.out
    assert "48000 Hz" in captured.out

def test_cli_storage_and_health_commands(mock_pedal_drive, capsys):
    """Tests storage stats and system health report via CLI."""
    sys.argv = ["headrush_cli.py", "storage"]
    cli.main()
    captured = capsys.readouterr()
    assert "STORAGE & CAPACITY STATUS" in captured.out
    assert "Slots Used:" in captured.out
    assert "Disk Total:" in captured.out

    sys.argv = ["headrush_cli.py", "health"]
    cli.main()
    captured = capsys.readouterr()
    assert "SYSTEM HEALTH SCORE" in captured.out
    assert "100%" in captured.out

def test_cli_cheatsheet_export(mock_pedal_drive, realistic_nam_files, tmp_path, capsys):
    """Tests exporting stage cheat sheets in multiple formats."""
    hm.install_nam_to_headrush(realistic_nam_files["wavenet"], custom_name="Stage Rhythm", slot=0)
    out_html = str(tmp_path / "stage_sheet.html")
    
    sys.argv = ["headrush_cli.py", "cheatsheet", "--format", "html", "-o", out_html]
    cli.main()
    captured = capsys.readouterr()
    assert "saved to:" in captured.out
    assert os.path.exists(out_html)
    with open(out_html, "r", encoding="utf-8") as f:
        content = f.read()
        assert "<table" in content
        assert "Stage Rhythm" in content

def test_cli_setlist_commands(mock_pedal_drive, realistic_nam_files, tmp_path, capsys):
    """Tests setlist lifecycle through CLI commands."""
    hm.install_nam_to_headrush(realistic_nam_files["wavenet"], custom_name="Rock Lead", slot=0)
    
    # Save
    sys.argv = ["headrush_cli.py", "setlist", "save", "--name", "Stadium_Gig"]
    cli.main()
    captured = capsys.readouterr()
    assert "saved to:" in captured.out

    # List
    sys.argv = ["headrush_cli.py", "setlist", "list"]
    cli.main()
    captured = capsys.readouterr()
    assert "Stadium_Gig" in captured.out

    # Export
    pack_path = str(tmp_path / "Stadium.hrpack")
    sys.argv = ["headrush_cli.py", "setlist", "export", "--name", "Stadium_Gig", "--target", pack_path]
    cli.main()
    assert os.path.exists(pack_path)
