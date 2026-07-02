import pytest

from pelican_mcp.client import PelicanConfig


def test_from_env_happy_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PELICAN_URL", "https://panel.example.com/")
    monkeypatch.setenv("PELICAN_TOKEN", "papp_abc")
    monkeypatch.delenv("PELICAN_CLIENT_TOKEN", raising=False)
    monkeypatch.delenv("PANEL_CLIENT_TOKEN", raising=False)
    monkeypatch.setenv("PELICAN_TIMEOUT", "45")
    monkeypatch.setenv("PELICAN_VERIFY_SSL", "false")

    cfg = PelicanConfig.from_env()
    assert cfg.panel_url == "https://panel.example.com"
    assert cfg.panel_token == "papp_abc"
    assert cfg.panel_client_token is None
    assert cfg.timeout == 45.0
    assert cfg.verify_ssl is False


def test_from_env_parses_client_token(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PELICAN_URL", "https://panel.example.com")
    monkeypatch.delenv("PELICAN_TOKEN", raising=False)
    monkeypatch.delenv("PANEL_TOKEN", raising=False)
    monkeypatch.setenv("PELICAN_CLIENT_TOKEN", "pacc_xyz")

    cfg = PelicanConfig.from_env()
    assert cfg.panel_token is None
    assert cfg.panel_client_token == "pacc_xyz"


def test_from_env_accepts_legacy_panel_names(monkeypatch, tmp_path):
    # The generic PANEL_* names still work (eases migrating a Pterodactyl-MCP config).
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PELICAN_URL", raising=False)
    monkeypatch.delenv("PELICAN_TOKEN", raising=False)
    monkeypatch.setenv("PANEL_URL", "https://panel.example.com")
    monkeypatch.setenv("PANEL_TOKEN", "papp_legacy")

    cfg = PelicanConfig.from_env()
    assert cfg.panel_url == "https://panel.example.com"
    assert cfg.panel_token == "papp_legacy"


def test_pelican_names_take_precedence(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PANEL_URL", "https://old.example.com")
    monkeypatch.setenv("PELICAN_URL", "https://new.example.com")
    monkeypatch.setenv("PELICAN_TOKEN", "papp_abc")

    cfg = PelicanConfig.from_env()
    assert cfg.panel_url == "https://new.example.com"


def test_from_env_missing_url(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PELICAN_URL", raising=False)
    monkeypatch.delenv("PANEL_URL", raising=False)
    monkeypatch.setenv("PELICAN_TOKEN", "papp_abc")
    with pytest.raises(ValueError, match="PELICAN_URL"):
        PelicanConfig.from_env()


def test_from_env_missing_both_tokens(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PELICAN_URL", "https://panel.example.com")
    monkeypatch.delenv("PELICAN_TOKEN", raising=False)
    monkeypatch.delenv("PELICAN_CLIENT_TOKEN", raising=False)
    monkeypatch.delenv("PANEL_TOKEN", raising=False)
    monkeypatch.delenv("PANEL_CLIENT_TOKEN", raising=False)
    with pytest.raises(ValueError, match="PELICAN_TOKEN"):
        PelicanConfig.from_env()
