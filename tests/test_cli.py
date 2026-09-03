import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

import headrush_cli as cli
import headrush_manager as hm

def test_cli_list_disconnected(capsys):
    orig_drive = hm.get_drive()
    try:
        hm.set_drive("Z:\\NON_EXISTENT_DRIVE_1234")
        class Args:
            pass
        cli.cmd_list(Args())
        captured = capsys.readouterr()
        assert "not detected" in captured.out
    finally:
        hm.set_drive(orig_drive)

def test_cli_irs_disconnected(capsys):
    orig_drive = hm.get_drive()
    try:
        hm.set_drive("Z:\\NON_EXISTENT_DRIVE_1234")
        class Args:
            pass
        cli.cmd_irs(Args())
        captured = capsys.readouterr()
        assert "not detected" in captured.out
    finally:
        hm.set_drive(orig_drive)

def test_database_search_sql():
    import sqlite3
    db_path = "c:/VM/TONE3000_NAM_Library/tone3000.db"
    if not os.path.exists(db_path):
        pytest.skip("Local Tone3000 database not present on this test runner")
        
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    sql = '''
        SELECT m.id, m.name, t.title, COALESCE(u.username, u.display_name, 'Community'),
               m.architecture_version, t.gear, m.local_path, t.description
        FROM models_fts fts
        JOIN models m ON fts.model_id = m.id
        JOIN tones t ON m.tone_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE models_fts MATCH ?
        LIMIT 5
    '''
    cur.execute(sql, ['"Dumble"*'])
    rows = cur.fetchall()
    conn.close()
    assert len(rows) > 0
    assert rows[0][1] is not None

def test_cli_storage_and_health(tmp_path, capsys):
    orig_drive = hm.get_drive()
    try:
        mock_drive = tmp_path / "cli_drive"
        os.makedirs(mock_drive / "NAM", exist_ok=True)
        os.makedirs(mock_drive / "Blocks" / "ANXIETY OD", exist_ok=True)
        os.makedirs(mock_drive / "Blocks" / "ANXIETY OD V2", exist_ok=True)
        hm.set_drive(str(mock_drive))

        class Args:
            pass

        cli.cmd_storage(Args())
        captured = capsys.readouterr()
        assert "STORAGE & CAPACITY STATUS" in captured.out

        cli.cmd_health(Args())
        captured = capsys.readouterr()
        assert "SYSTEM HEALTH SCORE" in captured.out
    finally:
        hm.set_drive(orig_drive)

def test_cli_cheatsheet_and_inspect(tmp_path, capsys):
    orig_drive = hm.get_drive()
    try:
        mock_drive = tmp_path / "cli_drive"
        os.makedirs(mock_drive / "NAM", exist_ok=True)
        os.makedirs(mock_drive / "Blocks" / "ANXIETY OD", exist_ok=True)
        os.makedirs(mock_drive / "Blocks" / "ANXIETY OD V2", exist_ok=True)
        hm.set_drive(str(mock_drive))

        # Create dummy file
        nam_file = mock_drive / "NAM" / "000 - Test Amp.nam"
        nam_file.write_text("{\"model\": 1}", encoding='utf-8')
        hm.create_block_preset(0, "Test Amp")

        class SheetArgs:
            format = "txt"
            output = None

        cli.cmd_cheatsheet(SheetArgs())
        captured = capsys.readouterr()
        assert "Test Amp" in captured.out

        class InspArgs:
            path = str(nam_file)

        cli.cmd_inspect(InspArgs())
        captured = capsys.readouterr()
        assert "NAM MODEL INSPECTOR" in captured.out
    finally:
        hm.set_drive(orig_drive)


