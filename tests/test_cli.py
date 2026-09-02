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

