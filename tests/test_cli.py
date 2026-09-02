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
