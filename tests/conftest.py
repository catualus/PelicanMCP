from __future__ import annotations

import os

import pytest

import pelican_mcp.client as client

_ENV_PREFIXES = ("PELICAN_", "PANEL_")


@pytest.fixture(autouse=True)
def isolate_panel_env(monkeypatch):
    """Run every test against an empty Pelican/Panel configuration.

    ``PelicanConfig.from_env`` reads ``os.environ`` and also calls
    ``load_dotenv(repo_root / ".env")``, so on a developer machine the real
    credentials leak into the test process: value assertions pick up the live
    panel URL, and the "missing env var must raise" tests never raise because
    the vars are present. Clear both sources — the ambient ``PELICAN_*`` /
    ``PANEL_*`` names, and the on-disk ``.env`` — so tests only see what they
    set themselves.
    """
    for name in list(os.environ):
        if name.startswith(_ENV_PREFIXES):
            monkeypatch.delenv(name, raising=False)

    monkeypatch.setattr(client, "load_dotenv", lambda *args, **kwargs: False)
