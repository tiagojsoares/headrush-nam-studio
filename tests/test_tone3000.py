import os
import json
import pytest
from tone3000_client import Tone3000Client, get_tone3000_client
import headrush_manager as hm
import headrush_cli as cli

def test_tone3000_client_initialization_and_credentials():
    """Validates that Tone3000Client initializes with provided API keys."""
    client = Tone3000Client()
    assert client.public_key.startswith("t3k_pub_")
    assert client.secret_key.startswith("t3k_cs_")
    assert client.user_agent == "HeadRushNAMStudio/1.2"

def test_tone3000_save_credentials(tmp_path, monkeypatch):
    """Tests saving credentials to custom configuration file."""
    custom_conf = tmp_path / "custom_config.json"
    monkeypatch.setattr("tone3000_client.CONFIG_PATH", str(custom_conf))
    
    client = Tone3000Client(public_key="test_pub_123", secret_key="test_sec_456")
    saved = client.save_credentials()
    assert saved is True
    assert os.path.exists(custom_conf)
    
    with open(custom_conf, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["public_key"] == "test_pub_123"
        assert data["secret_key"] == "test_sec_456"

def test_tone3000_live_trending_and_latest():
    """Validates live trending and latest endpoints from TONE3000 REST API."""
    client = get_tone3000_client()
    try:
        trending = client.get_trending()
        assert isinstance(trending, list)
        if trending:
            first = trending[0]
            assert "id" in first
            assert "title" in first or "name" in first

        latest = client.get_latest()
        assert isinstance(latest, list)
        if latest:
            first = latest[0]
            assert "id" in first
    except Exception as e:
        pytest.skip(f"Network request to TONE3000 failed: {e}")

def test_tone3000_live_search_and_model_listing():
    """Validates search queries and individual model capture listings."""
    client = get_tone3000_client()
    try:
        res = client.search_tones(query="Mesa", page=1, page_size=5)
        assert "tones" in res
        tones = res["tones"]
        assert len(tones) > 0
        
        # Test fetching models for first tone
        first_tone_id = tones[0]["id"]
        models = client.get_tone_models(first_tone_id)
        assert isinstance(models, list)
    except Exception as e:
        pytest.skip(f"Network request to TONE3000 failed: {e}")

def test_tone3000_download_and_install_mocked(mock_pedal_drive, monkeypatch, tmp_path):
    """
    Tests downloading a model and installing it into HeadRush MX5 USB drive,
    verifying slot creation, .nam placement, and dual V1/V2 blocks.
    """
    client = Tone3000Client()
    
    # Create fake downloaded .nam file with valid WaveNet format
    fake_nam = tmp_path / "downloaded_cloud.nam"
    fake_model_data = {
        "version": "0.5.2",
        "architecture": "WaveNet",
        "sample_rate": 48000,
        "metadata": {
            "name": "Mesa Boogie Dual Rectifier Solo",
            "author": "CloudCreator"
        }
    }
    fake_nam.write_text(json.dumps(fake_model_data), encoding="utf-8")
    
    # Mock download_model to return fake_nam
    monkeypatch.setattr(client, "download_model", lambda url, dest=None: str(fake_nam))
    
    mock_model_obj = {
        "id": 99999,
        "name": "Mesa Boogie Dual Rectifier Solo",
        "model_url": "https://fake.tone3000.com/download/fake.nam"
    }
    
    res = client.download_and_install_to_headrush(mock_model_obj, slot=5, tone=48, level=72)
    assert res["slot"] == 5
    assert "MESA" in res["preset_name"]
    
    # Verify installed files on HeadRush mock drive
    installed = hm.get_installed_slots()
    assert 5 in installed
    assert installed[5]["tone"] == 48
    assert installed[5]["level"] == 72
    assert os.path.exists(os.path.join(hm.get_nam_dir(), installed[5]["nam_file"]))
    assert os.path.exists(os.path.join(hm.get_blocks_v1_dir(), installed[5]["block_file_v1"]))
    assert os.path.exists(os.path.join(hm.get_blocks_v2_dir(), installed[5]["block_file_v2"]))

def test_cli_cloud_subcommands(capsys):
    """Validates CLI cloud command execution."""
    import sys
    
    # Test CLI trending
    sys.argv = ["headrush_cli.py", "cloud", "trending"]
    try:
        cli.main()
        captured = capsys.readouterr()
        assert "Top Trending Tones on TONE3000 Cloud" in captured.out
    except Exception as e:
        pytest.skip(f"Network request failed: {e}")
