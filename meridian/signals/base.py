from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Sequence

from meridian.db.models import MarketReport


@dataclass
class SignalResult:
    """Result of a signal evaluation."""

    raw_value: float
    computed_output: dict[str, Any]
    confidence: float
    fired: bool


class SignalEvaluator(ABC):
    """Base class for signal evaluators."""

    name: str

    @abstractmethod
    async def evaluate(
        self,
        geography: str,
        history: Sequence[MarketReport],
    ) -> SignalResult:
        """Evaluate the signal for a geography given historical market data."""
        ...


class SignalEngine:
    """Engine for evaluating signals against market data."""

    def __init__(self, evaluators: dict[str, SignalEvaluator]) -> None:
        self.evaluators = evaluators

    async def evaluate_signal(
        self,
        signal_name: str,
        geography: str,
        history: Sequence[MarketReport],
    ) -> SignalResult:
        """Evaluate a specific signal."""
        if signal_name not in self.evaluators:
            raise ValueError(f"Unknown signal: {signal_name}")

        evaluator = self.evaluators[signal_name]
        return await evaluator.evaluate(geography, history)
