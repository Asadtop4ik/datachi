"""Faza 5 darvozasi: UI moduli xatosiz import bo'ladi (st chaqiruvlari main() ichida)."""

from __future__ import annotations

import importlib

import requests


def test_ui_module_imports() -> None:
    mod = importlib.import_module("src.ui.app")
    assert callable(mod.main)
    assert callable(mod.call_api)


def test_call_api_handles_connection_error(monkeypatch) -> None:
    from src.ui import app

    def boom(*args, **kwargs):
        raise requests.exceptions.ConnectionError("no server")

    monkeypatch.setattr(app.requests, "post", boom)
    result = app.call_api("test", None)
    assert result["rows"] == []
    assert result["vega_spec"] is None
    assert "API" in result["text"]
    assert result["error_detail"]
