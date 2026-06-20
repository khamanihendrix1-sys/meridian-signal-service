from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import yaml

from meridian.settings import settings

if TYPE_CHECKING:
    from meridian.adapters.base import MarketAdapter


class AdapterRegistry:
    """Registry for market adapters with geography-based resolution."""

    def __init__(self) -> None:
        self._adapters: dict[str, MarketAdapter] = {}

    def register(self, adapter: MarketAdapter) -> None:
        """Register an adapter by name."""
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> MarketAdapter:
        """Get an adapter by name."""
        if name not in self._adapters:
            raise ValueError(f"Adapter '{name}' not registered")
        return self._adapters[name]

    def for_geography(self, geo: str) -> MarketAdapter:
        """Resolve which adapter serves a given geography (config-driven)."""
        config = self._load_config()
        default_adapter = config.get("default", "mock")

        for override in config.get("overrides", []):
            pattern = override["geography_pattern"]
            if re.match(pattern, geo):
                return self.get(override["adapter"])

        return self.get(default_adapter)

    def _load_config(self) -> dict[str, Any]:
        """Load adapter configuration from YAML."""
        config_path = settings.config_dir / "adapters.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
