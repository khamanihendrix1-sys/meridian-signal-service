from __future__ import annotations

import importlib
import sys
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_importing_main_does_not_require_runtime_env_vars(
    monkeypatch: MonkeyPatch,
) -> None:
    for env_var in (
        "DATABASE_URL",
        "REDIS_URL",
        "JWT_SIGNING_KEY",
    ):
        monkeypatch.delenv(env_var, raising=False)

    import meridian.settings

    meridian.settings.get_settings.cache_clear()
    sys.modules.pop("meridian.main", None)

    module = importlib.import_module("meridian.main")
    assert module.app is not None
