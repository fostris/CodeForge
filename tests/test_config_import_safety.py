"""Tests for config modules import/initialization safety."""

import importlib.util
import sys
import types
from pathlib import Path

from src.config import Settings as RootSettings


def test_root_settings_can_be_created_with_defaults():
    settings = RootSettings()
    assert settings is not None
    assert settings.log_level


def test_workspace_config_import_has_no_settings_side_effect():
    module_path = Path(__file__).parent.parent / "workspace" / "src" / "config.py"
    spec = importlib.util.spec_from_file_location("workspace_config_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    fake_passlib = types.ModuleType("passlib")
    fake_passlib_context = types.ModuleType("passlib.context")

    class _FakeCryptContext:
        def __init__(self, *args, **kwargs):
            self._schemes = kwargs.get("schemes", [])

        def schemes(self):
            return self._schemes

    fake_passlib_context.CryptContext = _FakeCryptContext
    sys.modules["passlib"] = fake_passlib
    sys.modules["passlib.context"] = fake_passlib_context
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop("passlib.context", None)
        sys.modules.pop("passlib", None)

    assert module._settings_instance is None
    assert callable(module.get_settings)
